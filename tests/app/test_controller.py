"""Tests for app/controller.py with fake keys and a fake process (offscreen Qt, no game)."""

from __future__ import annotations

import pytest

from actrainer import offsets
from actrainer.features.primitives import OverlayFrame, Rect
from actrainer.game.player import read_player
from actrainer.input.actions import (
    AIMBOT_ACTIVATE,
    ESP_TOGGLE,
    FREEZE_GAME_FOV,
    MENU_TOGGLE,
    PANIC,
    QUIT,
    BindMode,
    freeze_action_id,
    set_action_id,
)
from actrainer.input.keys import VK_END, VK_INSERT, VK_RBUTTON
from actrainer.memory.process import AttachError
from actrainer.app.controller import Controller
from actrainer.maths.angles import calc_aim_angles
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from helpers import gl_matrix as gl
from helpers.fake_game import make_fake_game

KEY_F7 = 0x76
KEY_F8 = 0x77
KEY_F9 = 0x78


class NoGame:
    """A process stand-in for 'the game isn't running'."""

    is_attached = False
    pid = 0
    module_base = 0
    attach_calls = 0

    def attach(self) -> None:
        NoGame.attach_calls += 1
        raise AttachError("not running")

    def detach(self) -> None:
        pass

    def is_alive(self) -> bool:
        return False


class Keys:
    """Feeds the controller a scripted set of pressed keys."""

    def __init__(self) -> None:
        self.down: set[int] = set()

    def __call__(self) -> set[int]:
        return set(self.down)


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        self.t += 1 / 60
        return self.t


def make(settings: Settings, signals: AppSignals) -> tuple[Controller, Keys]:
    keys = Keys()
    return Controller(settings, signals, process=NoGame(), key_source=keys, clock=Clock()), keys  # type: ignore[arg-type]


def press(controller: Controller, keys: Keys, vk: int) -> None:
    keys.down = {vk}
    controller.tick()
    keys.down = set()
    controller.tick()


def test_menu_toggle_and_quit_emit(settings: Settings, signals: AppSignals) -> None:
    settings.keybinds.binds[QUIT].key = KEY_F7
    controller, keys = make(settings, signals)
    events: list[str] = []
    signals.menu_toggle_requested.connect(lambda: events.append("menu"))
    signals.quit_requested.connect(lambda: events.append("quit"))
    press(controller, keys, VK_INSERT)
    press(controller, keys, KEY_F7)
    assert events == ["menu", "quit"]


def test_panic_disables_everything(settings: Settings, signals: AppSignals) -> None:
    settings.aimbot.enabled = True
    settings.esp.enabled = True
    settings.player.values["health"].freeze = True
    settings.player.ammo["smg"].freeze = True
    controller, keys = make(settings, signals)
    refreshes: list[bool] = []
    signals.refresh_requested.connect(lambda: refreshes.append(True))
    press(controller, keys, VK_END)
    assert not settings.aimbot.enabled and not settings.esp.enabled
    assert not settings.player.values["health"].freeze and not settings.player.ammo["smg"].freeze
    assert refreshes  # UI told to reload


def test_toggle_hotkeys_flip_settings(settings: Settings, signals: AppSignals) -> None:
    settings.keybinds.binds[ESP_TOGGLE].key = KEY_F8
    settings.keybinds.binds[freeze_action_id("sniper")].key = KEY_F9
    controller, keys = make(settings, signals)
    press(controller, keys, KEY_F8)
    press(controller, keys, KEY_F9)
    assert settings.esp.enabled is True
    assert settings.player.ammo["sniper"].freeze is True


def test_set_value_hotkey_requests_write(settings: Settings, signals: AppSignals) -> None:
    settings.keybinds.binds[set_action_id("health")].key = KEY_F8
    controller, keys = make(settings, signals)
    requested: list[str] = []
    signals.set_value_requested.connect(requested.append)
    press(controller, keys, KEY_F8)
    assert requested == ["health"]


def test_keybinds_suspended_while_capturing(settings: Settings, signals: AppSignals) -> None:
    controller, keys = make(settings, signals)
    events: list[str] = []
    signals.menu_toggle_requested.connect(lambda: events.append("menu"))
    signals.bind_capture_changed.emit(True)
    press(controller, keys, VK_INSERT)
    signals.bind_capture_changed.emit(False)
    assert events == []
    assert settings.keybinds.binds[MENU_TOGGLE].key == VK_INSERT


def test_attach_retry_is_throttled(settings: Settings, signals: AppSignals) -> None:
    controller, _ = make(settings, signals)
    NoGame.attach_calls = 0
    for _ in range(120):  # two simulated seconds at 60 Hz
        controller.tick()
    assert 1 <= NoGame.attach_calls <= 3  # about once per second, not every tick


def test_status_when_not_attached(settings: Settings, signals: AppSignals) -> None:
    controller, _ = make(settings, signals)
    statuses: list = []
    signals.status_changed.connect(statuses.append)
    for _ in range(60):
        controller.tick()
    assert statuses and not statuses[-1].attached
    assert statuses[-1].tick_rate > 0


def test_tick_rate_change_updates_timer(settings: Settings, signals: AppSignals) -> None:
    controller, _ = make(settings, signals)
    settings.general.tick_rate_hz = 120
    signals.settings_changed.emit("general")
    assert controller._timer.interval() == 8  # noqa: SLF001 - round(1000/120)


def test_panic_action_id_is_end_by_default(settings: Settings) -> None:
    assert settings.keybinds.binds[PANIC].key == VK_END


# --- aimbot wiring (Phase 6) ---------------------------------------------------------------

def make_attached(settings: Settings, signals: AppSignals, focused: bool = True):  # noqa: ANN201
    # Local at (10, 20) looking along +x (yaw 90); one bot ahead and a bit to the side.
    proc, local, bots = make_fake_game(local={"yaw": 90.0, "pitch": 0.0, "head": (10.0, 20.0, 5.5),
                                              "feet": (10.0, 20.0, 1.0)},
                                       bots=[{"name": b"Target", "head": (60.0, 25.0, 5.5), "feet": (60.0, 25.0, 1.0)}])
    keys = Keys()
    controller = Controller(settings, signals, process=proc, key_source=keys, clock=Clock(),  # type: ignore[arg-type]
                            focus_check=lambda _hwnd: focused)
    return controller, keys, proc, local


def test_aimbot_snaps_when_enabled_key_held_and_focused(settings: Settings, signals: AppSignals) -> None:
    settings.aimbot.enabled = True
    settings.aimbot.smoothing = 1.0
    controller, keys, proc, local = make_attached(settings, signals)
    keys.down = {VK_RBUTTON}
    controller.tick()
    me = read_player(proc, local)
    expected = calc_aim_angles(me.head, controller.state.entities[0].head)
    assert (me.yaw, me.pitch) == pytest.approx(tuple(expected), abs=1e-3)
    assert controller.aim_target_address == controller.state.entities[0].address


@pytest.mark.parametrize("enabled, held, focused", [(False, True, True), (True, False, True), (True, True, False)])
def test_aimbot_does_nothing_unless_all_conditions(settings: Settings, signals: AppSignals,
                                                   enabled: bool, held: bool, focused: bool) -> None:
    settings.aimbot.enabled = enabled
    controller, keys, proc, _ = make_attached(settings, signals, focused=focused)
    keys.down = {VK_RBUTTON} if held else set()
    controller.tick()
    assert proc.writes == []


def test_aimbot_toggle_mode(settings: Settings, signals: AppSignals) -> None:
    settings.aimbot.enabled = True
    settings.keybinds.binds[AIMBOT_ACTIVATE].mode = BindMode.TOGGLE
    controller, keys, proc, _ = make_attached(settings, signals)
    keys.down = {VK_RBUTTON}
    controller.tick()   # press: toggled on
    keys.down = set()
    proc.writes.clear()
    controller.tick()   # released but still on
    assert proc.writes


def test_entity_count_in_status(settings: Settings, signals: AppSignals) -> None:
    controller, _, _, _ = make_attached(settings, signals)
    controller.tick()
    assert controller.status().entity_count == 1 and controller.status().offsets_ok


# --- player values (Phase 7) ----------------------------------------------------------------

def health_of(proc, address: int) -> int:  # noqa: ANN001
    return read_player(proc, address).health


def test_set_now_writes_once_and_notifies(settings: Settings, signals: AppSignals) -> None:
    settings.player.values["health"].target = 999
    controller, _, proc, local = make_attached(settings, signals)
    notices: list[str] = []
    signals.notice.connect(notices.append)
    signals.set_value_requested.emit("health")
    controller.tick()
    assert health_of(proc, local) == 999
    assert notices == ["Health set to 999"]
    # Game changes it back (took damage): no freeze, so it stays changed.
    proc.write_i32(local + offsets.HEALTH, 40)
    controller.tick()
    assert health_of(proc, local) == 40


def test_freeze_reapplies_every_tick(settings: Settings, signals: AppSignals) -> None:
    settings.player.values["health"].target = 500
    settings.player.values["health"].freeze = True
    controller, _, proc, local = make_attached(settings, signals)
    controller.tick()
    assert health_of(proc, local) == 500
    proc.write_i32(local + offsets.HEALTH, 12)   # took damage
    controller.tick()
    assert health_of(proc, local) == 500
    proc.writes.clear()
    controller.tick()
    assert proc.writes == []                      # already correct: no redundant write


def test_weapon_set_now_writes_mag_and_reserve(settings: Settings, signals: AppSignals) -> None:
    settings.player.ammo["assault"].mag = 33
    settings.player.ammo["assault"].reserve = 444
    controller, _, proc, local = make_attached(settings, signals)
    signals.set_value_requested.emit("assault")
    controller.tick()
    me = read_player(proc, local)
    assert (me.mag_ammo["assault"], me.reserve_ammo["assault"]) == (33, 444)


def test_set_now_while_dead_is_refused(settings: Settings, signals: AppSignals) -> None:
    controller, _, proc, local = make_attached(settings, signals)
    proc.write_i32(local + offsets.DEAD, 1)
    proc.writes.clear()
    notices: list[str] = []
    signals.notice.connect(notices.append)
    signals.set_value_requested.emit("health")
    controller.tick()
    assert proc.writes == [] and "dead" in notices[0]


def test_set_now_when_not_in_match_is_dropped(settings: Settings, signals: AppSignals) -> None:
    controller, _ = make(settings, signals)  # NoGame: never attaches
    notices: list[str] = []
    signals.notice.connect(notices.append)
    signals.set_value_requested.emit("health")
    controller.tick()
    controller.tick()
    assert notices == ["Not in a match: nothing written"]  # once, not every tick


def test_panic_stops_freezing(settings: Settings, signals: AppSignals) -> None:
    settings.player.values["health"].target = 500
    settings.player.values["health"].freeze = True
    controller, keys, proc, local = make_attached(settings, signals)
    controller.tick()
    keys.down = {VK_END}
    controller.tick()
    keys.down = set()
    proc.write_i32(local + offsets.HEALTH, 12)
    controller.tick()
    assert health_of(proc, local) == 12


def test_status_carries_live_player_values(settings: Settings, signals: AppSignals) -> None:
    controller, _, _, _ = make_attached(settings, signals)
    controller.tick()
    values = controller.status().player_values
    assert values["health"] == 100 and values["mag:pistol"] == 10


# --- overlay frames (Phase 9) -----------------------------------------------------------------


def make_overlay_controller(settings: Settings, signals: AppSignals, game_focused: bool, app_focused: bool):  # noqa: ANN201
    proc, _, _ = make_fake_game(local={"yaw": 90.0, "head": (0.0, 0.0, 4.5), "feet": (0.0, 0.0, 0.0)},
                                bots=[{"name": b"Ahead", "head": (50.0, 0.0, 4.5), "feet": (50.0, 0.0, 0.0)}],
                                matrix=gl.ac_view_projection((0.0, 0.0, 4.5), 90.0, 0.0, width=800, height=600))
    frames: list[OverlayFrame] = []
    signals.overlay_frame.connect(frames.append)
    controller = Controller(settings, signals, process=proc, key_source=Keys(), clock=Clock(),  # type: ignore[arg-type]
                            focus_check=lambda _h: game_focused, app_focus_check=lambda: app_focused,
                            client_rect=lambda _h: (100, 50, 800, 600))
    return controller, frames


def test_overlay_frame_sent_when_game_focused(settings: Settings, signals: AppSignals) -> None:
    settings.esp.enabled = True
    controller, frames = make_overlay_controller(settings, signals, game_focused=True, app_focused=False)
    controller.tick()
    frame = frames[-1]
    assert frame.visible and (frame.x, frame.y, frame.width, frame.height) == (100, 50, 800, 600)
    assert any(isinstance(p, Rect) for p in frame.primitives)


def test_overlay_visible_while_menu_focused(settings: Settings, signals: AppSignals) -> None:
    settings.esp.enabled = True
    controller, frames = make_overlay_controller(settings, signals, game_focused=False, app_focused=True)
    controller.tick()
    assert frames[-1].visible


def test_overlay_hidden_when_something_else_focused_and_hide_sent_once(settings: Settings, signals: AppSignals) -> None:
    settings.esp.enabled = True
    controller, frames = make_overlay_controller(settings, signals, game_focused=True, app_focused=False)
    controller.tick()
    controller._focus_check = lambda _h: False  # noqa: SLF001 - user alt-tabs to another app
    controller.tick()
    controller.tick()
    assert [f.visible for f in frames] == [True, False]


def test_overlay_hidden_when_nothing_to_draw(settings: Settings, signals: AppSignals) -> None:
    controller, frames = make_overlay_controller(settings, signals, game_focused=True, app_focused=False)
    controller.tick()  # ESP and aimbot both off by default
    assert frames == []


# --- game FOV (Phase 10) --------------------------------------------------------------------------

def fov_of(proc) -> float:  # noqa: ANN001
    return proc.read_f32(proc.module_base + offsets.VIEW_FOV)


def test_game_fov_set_now_and_notice(settings: Settings, signals: AppSignals) -> None:
    settings.view.fov = 110.0
    controller, _, proc, _ = make_attached(settings, signals)
    notices: list[str] = []
    signals.notice.connect(notices.append)
    signals.game_fov_set_requested.emit()
    controller.tick()
    assert fov_of(proc) == 110.0 and notices == ["Game FOV set to 110°"]
    controller.tick()
    assert controller.status().game_fov == 110.0


def test_game_fov_keep_applied_and_panic_restores_original(settings: Settings, signals: AppSignals) -> None:
    settings.view.fov = 120.0
    settings.view.freeze = True
    controller, keys, proc, _ = make_attached(settings, signals)
    controller.tick()
    assert fov_of(proc) == 120.0
    proc.write_f32(proc.module_base + offsets.VIEW_FOV, 80.0)  # the game resets it
    controller.tick()
    assert fov_of(proc) == 120.0
    keys.down = {VK_END}
    controller.tick()
    assert fov_of(proc) == 90.0            # original restored
    assert settings.view.freeze is False


def test_game_fov_restored_on_shutdown(settings: Settings, signals: AppSignals) -> None:
    settings.view.fov = 60.0
    controller, _, proc, _ = make_attached(settings, signals)
    signals.game_fov_set_requested.emit()
    controller.tick()
    assert fov_of(proc) == 60.0
    controller.shutdown()
    assert fov_of(proc) == 90.0


def test_freeze_fov_hotkey(settings: Settings, signals: AppSignals) -> None:
    settings.keybinds.binds[FREEZE_GAME_FOV].key = KEY_F8
    controller, keys, _, _ = make_attached(settings, signals)
    keys.down = {KEY_F8}
    controller.tick()
    assert settings.view.freeze is True
