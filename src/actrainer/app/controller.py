"""The main tick loop.

A QTimer fires at settings.general.tick_rate_hz. Each tick:
    1. poll keybinds (suspended while the menu captures a bind) and handle actions
    2. make sure we're attached (throttled retry; detach if the game died)
    3. read the game state (local player + live bots)
    4. aimbot -> write view angles (only while enabled, key active and the GAME window is focused)
    5. player values: set-now + freezes             [Phase 7]
    6. ESP -> draw primitives -> overlay repaint     [Phase 9]
    7. emit status to the menu (throttled)
Read errors are logged and the tick is skipped. Nothing here may crash the app.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from PyQt5.QtCore import QObject, QTimer

from actrainer import config
from actrainer.app.status import ControllerStatus
from actrainer.features import aimbot
from actrainer.game.local_player import write_view_angles
from actrainer.game.state import read_game_state
from actrainer.game.structs import GameState
from actrainer.input import actions
from actrainer.input.keybinds import ActionStates, KeybindEngine
from actrainer.input.keys import BINDABLE_VKS
from actrainer.memory.process import AttachError, GameProcess, MemoryAccessError
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.winapi import win32

log = logging.getLogger(__name__)

MS_PER_SECOND = 1000


def default_key_source() -> set[int]:
    """Currently pressed bindable keys (real keyboard/mouse)."""
    return win32.get_pressed_keys(BINDABLE_VKS)


def default_focus_check(game_hwnd: int | None) -> bool:
    """True if the game window is the foreground window."""
    return game_hwnd is not None and win32.get_foreground_window() == game_hwnd


class Controller(QObject):
    """Owns the game connection and the tick timer. The UI never calls memory code; this does."""

    def __init__(self, settings: Settings, signals: AppSignals, process: GameProcess | None = None,
                 key_source: Callable[[], set[int]] = default_key_source,
                 clock: Callable[[], float] = time.perf_counter,
                 focus_check: Callable[[int | None], bool] = default_focus_check) -> None:
        super().__init__()
        self.settings = settings
        self.signals = signals
        self.process = process or GameProcess()
        self._key_source = key_source
        self._clock = clock
        self._focus_check = focus_check
        self._engine = KeybindEngine()
        self._capturing = False
        self._game_hwnd: int | None = None
        self._exe_version: str | None = None
        self._next_attach = 0.0
        self._next_liveness = 0.0
        self._next_status = 0.0
        self._last_tick: float | None = None
        self._tick_rate = 0.0
        self._offsets_ok = False
        self._entity_count = 0
        self._game_focused = False
        self.state: GameState | None = None   # latest snapshot (None = not in a match)
        self.aim_target_address: int | None = None  # bot currently being aimed at (for ESP highlight later)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)
        signals.settings_changed.connect(self._on_settings_changed)
        signals.bind_capture_changed.connect(self._on_capture)
        signals.set_value_requested.connect(self._on_set_value)

    # --- lifecycle -------------------------------------------------------------------

    def start(self) -> None:
        self._apply_tick_rate()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def shutdown(self) -> None:
        """Stop ticking and release the game (called on quit)."""
        self.stop()
        self.settings.player.unfreeze_all()
        self.process.detach()

    @property
    def game_hwnd(self) -> int | None:
        """The game's main window handle, if attached and found."""
        return self._game_hwnd if win32.is_window(self._game_hwnd) else None

    # --- tick ---------------------------------------------------------------------------

    def tick(self) -> None:
        """One iteration of the main loop. Never raises."""
        try:
            now = self._clock()
            self._measure_rate(now)
            states = self._engine.update(self._key_source(), self.settings.keybinds.binds, suspended=self._capturing)
            self._handle_actions(states)
            self.aim_target_address = None
            if self._ensure_attached(now):
                self._game_focused = self._focus_check(self.game_hwnd)
                if self._read_game():
                    self._run_aimbot(states)
            if now >= self._next_status:
                self._next_status = now + config.STATUS_INTERVAL_S
                self.signals.status_changed.emit(self.status())
        except Exception:  # noqa: BLE001 - the loop must survive anything; log with traceback
            log.exception("tick failed")

    def _measure_rate(self, now: float) -> None:
        if self._last_tick is not None and now > self._last_tick:
            sample = 1.0 / (now - self._last_tick)
            a = config.TICK_RATE_SMOOTHING
            self._tick_rate = sample if self._tick_rate == 0 else (1 - a) * self._tick_rate + a * sample
        self._last_tick = now

    def _ensure_attached(self, now: float) -> bool:
        """Attach (throttled) if needed; detect a closed game. Returns True when attached."""
        if self.process.is_attached:
            if now >= self._next_liveness:
                self._next_liveness = now + config.LIVENESS_CHECK_S
                if not self.process.is_alive():
                    log.info("game closed; waiting for it to come back")
                    self._detach()
                    return False
            return True
        if now < self._next_attach:
            return False
        self._next_attach = now + config.ATTACH_RETRY_S
        try:
            self.process.attach()
        except AttachError:
            return False
        self._next_liveness = now + config.LIVENESS_CHECK_S
        self._game_hwnd = win32.find_main_window(self.process.pid)
        path = win32.get_process_image_path(self.process.pid)
        self._exe_version = win32.get_file_version(path) if path else None
        return True

    def _detach(self) -> None:
        self.process.detach()
        self._game_hwnd = None
        self._offsets_ok = False
        self._entity_count = 0
        self._game_focused = False
        self.state = None

    def _read_game(self) -> bool:
        """Read this tick's GameState into self.state. Returns True if we're in a match."""
        try:
            self.state = read_game_state(self.process)
        except MemoryAccessError as exc:
            log.debug("read failed, skipping tick: %s", exc)
            self.state = None
        self._offsets_ok = self.state is not None
        self._entity_count = len(self.state.entities) if self.state else 0
        if self._game_hwnd is None:
            self._game_hwnd = win32.find_main_window(self.process.pid)
        return self.state is not None

    def _run_aimbot(self, states: ActionStates) -> None:
        """Aim only when enabled, the activation key is active, and the game (not the menu) is focused."""
        aim = self.settings.aimbot
        if not (aim.enabled and states.is_active(actions.AIMBOT_ACTIVATE) and self._game_focused):
            return
        assert self.state is not None
        result = aimbot.compute_aim(self.state.local, self.state.entities, aim)
        if result is None:
            return
        angles, target = result
        self.aim_target_address = target.player.address
        try:
            write_view_angles(self.process, self.state.local.address, angles)
        except MemoryAccessError as exc:
            log.debug("angle write failed: %s", exc)

    # --- actions ----------------------------------------------------------------------

    def _handle_actions(self, states: ActionStates) -> None:
        if states.fired(actions.PANIC):
            self.panic()
        if states.fired(actions.MENU_TOGGLE):
            self.signals.menu_toggle_requested.emit()
        if states.fired(actions.QUIT):
            self.signals.quit_requested.emit()
        if states.fired(actions.ESP_TOGGLE):
            self._flip("esp", "enabled")
        if states.fired(actions.AIMBOT_ENABLE_TOGGLE):
            self._flip("aimbot", "enabled")
        for value_id in (*config.STAT_VALUES, *config.WEAPONS):
            if states.fired(actions.set_action_id(value_id)):
                self.signals.set_value_requested.emit(value_id)
            if states.fired(actions.freeze_action_id(value_id)):
                setting = (self.settings.player.values.get(value_id) or self.settings.player.ammo[value_id])
                setting.freeze = not setting.freeze
                self._announce("player")

    def _flip(self, section: str, field: str) -> None:
        obj = getattr(self.settings, section)
        setattr(obj, field, not getattr(obj, field))
        log.info("%s.%s -> %s (hotkey)", section, field, getattr(obj, field))
        self._announce(section)

    def _announce(self, section: str) -> None:
        """Settings changed outside the widgets: mark dirty and make the UI reload."""
        self.signals.settings_changed.emit(section)
        self.signals.refresh_requested.emit()

    def panic(self) -> None:
        """Instantly disable every feature and unfreeze every value."""
        self.settings.aimbot.enabled = False
        self.settings.esp.enabled = False
        self.settings.player.unfreeze_all()
        self._engine.reset_toggles()
        log.warning("PANIC: all features disabled, all values unfrozen")
        self._announce("panic")

    # --- signal handlers ----------------------------------------------------------------------

    def _on_settings_changed(self, section: str) -> None:
        if section == "general":
            self._apply_tick_rate()

    def _on_capture(self, capturing: bool) -> None:
        self._capturing = capturing

    def _on_set_value(self, value_id: str) -> None:
        log.info("set-now requested for %s (writes arrive in Phase 7)", value_id)

    def _apply_tick_rate(self) -> None:
        self._timer.setInterval(max(1, round(MS_PER_SECOND / self.settings.general.tick_rate_hz)))

    # --- status ---------------------------------------------------------------------------

    def status(self) -> ControllerStatus:
        attached = self.process.is_attached
        hwnd = self.game_hwnd
        return ControllerStatus(
            attached=attached,
            pid=self.process.pid if attached else 0,
            module_base=self.process.module_base if attached else 0,
            exe_version=self._exe_version if attached else None,
            offsets_ok=self._offsets_ok,
            in_match=self._offsets_ok,
            entity_count=self._entity_count,
            tick_rate=self._tick_rate,
            game_focused=self._game_focused if hwnd is not None else False,
        )
