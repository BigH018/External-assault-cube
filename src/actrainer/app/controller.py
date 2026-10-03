"""The main tick loop.

A QTimer fires at settings.general.tick_rate_hz. Each tick:
    1. poll keybinds (suspended while the menu captures a bind) and handle actions
    2. make sure we're attached (throttled retry; detach if the game died)
    3. read the game state (local player + live bots)
    4. aimbot -> write view angles (only while enabled, key active and the GAME window is focused)
    5. player values: pending set-now requests + freezes -> int writes (skipped while dead);
       game FOV: set-now / keep-applied (original FOV restored on panic and quit)
    6. ESP + FOV circle -> OverlayFrame (client rect + primitives) -> overlay (visible only while the
       game or our own menu is focused)
    7. emit status to the menu (throttled)
Read errors are logged and the tick is skipped. Nothing here may crash the app.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from PyQt5.QtCore import QObject, Qt, QTimer
from PyQt5.QtWidgets import QApplication

from actrainer import config
from actrainer.app.status import ControllerStatus
from actrainer.features import aimbot, esp, game_fov, player_values
from actrainer.features.primitives import OverlayFrame
from actrainer.game.local_player import VALUE_FIELD_OFFSETS, snapshot_value, write_player_value, write_view_angles
from actrainer.game.state import read_game_state
from actrainer.game.view import write_fov
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


def default_app_focus_check() -> bool:
    """True if one of OUR windows (the menu or a dialog) is the active foreground window."""
    return QApplication.activeWindow() is not None


def default_client_rect(game_hwnd: int | None) -> tuple[int, int, int, int] | None:
    """The game's client area on screen, or None if there's no usable (non-minimised) window."""
    if game_hwnd is None or win32.is_minimized(game_hwnd):
        return None
    rect = win32.get_client_rect_on_screen(game_hwnd)
    return rect if rect and rect[2] > 0 and rect[3] > 0 else None


class Controller(QObject):
    """Owns the game connection and the tick timer. The UI never calls memory code; this does."""

    def __init__(self, settings: Settings, signals: AppSignals, process: GameProcess | None = None,
                 key_source: Callable[[], set[int]] = default_key_source,
                 clock: Callable[[], float] = time.perf_counter,
                 focus_check: Callable[[int | None], bool] = default_focus_check,
                 app_focus_check: Callable[[], bool] = default_app_focus_check,
                 client_rect: Callable[[int | None], tuple[int, int, int, int] | None] = default_client_rect) -> None:
        super().__init__()
        self.settings = settings
        self.signals = signals
        self.process = process or GameProcess()
        self._key_source = key_source
        self._clock = clock
        self._focus_check = focus_check
        self._app_focus_check = app_focus_check
        self._client_rect = client_rect
        self._overlay_visible = False
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
        self._pending_sets: list[str] = []          # value ids from "Set now" buttons/hotkeys, applied next tick
        self._fov_requested = False                 # "Set game FOV now" pending
        self._original_fov: float | None = None     # game FOV before our first write (restored on panic/quit)

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)  # the default coarse timer (~15.6 ms steps) makes 60 Hz uneven
        self._timer.timeout.connect(self.tick)
        signals.settings_changed.connect(self._on_settings_changed)
        signals.bind_capture_changed.connect(self._on_capture)
        signals.set_value_requested.connect(self._on_set_value)
        signals.game_fov_set_requested.connect(self._on_set_fov)

    # --- lifecycle -------------------------------------------------------------------

    def start(self) -> None:
        self._apply_tick_rate()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def shutdown(self) -> None:
        """Stop ticking and release the game (called on quit)."""
        self.stop()
        self.signals.overlay_frame.emit(OverlayFrame())  # hide the overlay
        self.settings.player.unfreeze_all()
        self._restore_fov()
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
                    self._apply_player_values()
                    self._apply_game_fov()
            self._drop_unapplied_sets()
            self._update_overlay()
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
        self._original_fov = None  # a restarted game starts from its own config again
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

    def _apply_player_values(self) -> None:
        """Write pending set-now values and frozen values (only fields that differ)."""
        assert self.state is not None
        local = self.state.local
        requested, self._pending_sets = self._pending_sets, []
        if requested and local.dead:
            self.signals.notice.emit("You're dead: values not written (try again after respawning)")
        for write in player_values.plan_writes(local, self.settings.player, requested):
            try:
                write_player_value(self.process, local.address, write.field, write.value)
            except MemoryAccessError as exc:
                log.debug("value write %s failed: %s", write.field, exc)
                continue
        if not local.dead:
            for value_id in requested:
                self.signals.notice.emit(player_values.describe(value_id, self.settings.player))

    def _apply_game_fov(self) -> None:
        """Write the game FOV for a set-now request or while keep-applied is on."""
        assert self.state is not None
        requested, self._fov_requested = self._fov_requested, False
        new = game_fov.plan_fov_write(self.state.fov, self.settings.view, requested)
        if new is None:
            if requested:
                self.signals.notice.emit(f"Game FOV is already {self.state.fov:g}°")
            return
        if self._original_fov is None:
            self._original_fov = self.state.fov
        try:
            write_fov(self.process, new)
        except MemoryAccessError as exc:
            log.debug("fov write failed: %s", exc)
            return
        if requested:
            self.signals.notice.emit(f"Game FOV set to {new:g}°")

    def _restore_fov(self) -> None:
        """Put the game's FOV back to what it was before we first changed it."""
        if self._original_fov is None or not self.process.is_attached:
            return
        try:
            write_fov(self.process, self._original_fov)
            log.info("game FOV restored to %g", self._original_fov)
        except MemoryAccessError as exc:
            log.debug("fov restore failed: %s", exc)
        self._original_fov = None

    def _drop_unapplied_sets(self) -> None:
        """Set-now requests that couldn't run this tick (not attached / not in a match) are dropped, with a notice."""
        if self._pending_sets or self._fov_requested:
            self._pending_sets = []
            self._fov_requested = False
            self.signals.notice.emit("Not in a match: nothing written")

    def _update_overlay(self) -> None:
        """Build this tick's ESP frame and send it to the overlay (or tell it to hide)."""
        frame = OverlayFrame()  # hidden
        rect = self._client_rect(self.game_hwnd) if self.state is not None else None
        if rect is not None and self.state is not None and (self._game_focused or self._app_focus_check()):
            x, y, w, h = rect
            primitives = esp.build_esp(self.state, self.settings.esp, self.settings.aimbot, w, h,
                                       self.aim_target_address)
            if primitives:
                frame = OverlayFrame(True, x, y, w, h, tuple(primitives))
        # Only emit "hidden" once, not every tick.
        if frame.visible or self._overlay_visible:
            self.signals.overlay_frame.emit(frame)
        self._overlay_visible = frame.visible

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
        if states.fired(actions.SET_GAME_FOV):
            self._fov_requested = True
        if states.fired(actions.FREEZE_GAME_FOV):
            self._flip("view", "freeze")
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
        self.settings.view.freeze = False
        self._restore_fov()
        self._engine.reset_toggles()
        log.warning("PANIC: all features disabled, all values unfrozen, FOV restored")
        self._announce("panic")

    # --- signal handlers ----------------------------------------------------------------------

    def _on_settings_changed(self, section: str) -> None:
        if section == "general":
            self._apply_tick_rate()

    def _on_capture(self, capturing: bool) -> None:
        self._capturing = capturing

    def _on_set_value(self, value_id: str) -> None:
        if value_id not in self._pending_sets:
            self._pending_sets.append(value_id)  # applied on the next tick, inside the normal read/write cycle

    def _on_set_fov(self) -> None:
        self._fov_requested = True

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
            game_fov=self.state.fov if self.state else 0.0,
            player_values=({f: snapshot_value(self.state.local, f) for f in VALUE_FIELD_OFFSETS}
                           if self.state else {}),
        )
