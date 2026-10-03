"""Tests for app/controller.py with fake keys and a fake process (offscreen Qt, no game)."""

from __future__ import annotations

from actrainer.input.actions import ESP_TOGGLE, MENU_TOGGLE, PANIC, QUIT, freeze_action_id, set_action_id
from actrainer.input.keys import VK_END, VK_INSERT
from actrainer.memory.process import AttachError
from actrainer.app.controller import Controller
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals

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
