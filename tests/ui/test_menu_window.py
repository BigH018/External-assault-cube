"""Smoke tests for ui/menu_window.py (offscreen): builds, title marker, keybind sync, status."""

from __future__ import annotations

from PyQt5.QtWidgets import QCheckBox

from actrainer.app.status import ControllerStatus
from actrainer.input.actions import AIMBOT_ACTIVATE, PANIC
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.ui.menu_window import MenuWindow
from actrainer.ui.profile_session import ProfileSession


def make(settings: Settings, signals: AppSignals, session: ProfileSession) -> MenuWindow:
    return MenuWindow(settings, signals, session, lambda: None)


def test_builds_with_five_tabs(settings: Settings, signals: AppSignals, session: ProfileSession) -> None:
    menu = make(settings, signals, session)
    assert [menu.tabs.tabText(i) for i in range(menu.tabs.count())] == ["Aimbot", "ESP", "Player", "Keybinds", "Settings"]


def test_title_shows_unsaved_marker(settings: Settings, signals: AppSignals, session: ProfileSession) -> None:
    menu = make(settings, signals, session)
    assert not menu.windowTitle().endswith("*")
    signals.settings_changed.emit("esp")
    assert menu.windowTitle().endswith("*")


def test_bind_change_on_one_tab_updates_the_other(settings: Settings, signals: AppSignals,
                                                  session: ProfileSession) -> None:
    menu = make(settings, signals, session)
    menu.aimbot_tab.keys.buttons[AIMBOT_ACTIVATE].keyChanged.emit(0x46)  # F on the Aimbot tab
    assert menu.keybinds_tab.keys.buttons[AIMBOT_ACTIVATE].text() == "F"


def test_conflict_banner(settings: Settings, signals: AppSignals, session: ProfileSession) -> None:
    menu = make(settings, signals, session)
    settings.keybinds.binds[PANIC].key = settings.keybinds.binds[AIMBOT_ACTIVATE].key
    signals.settings_changed.emit("keybinds")
    assert not menu.keybinds_tab._banner.isHidden()  # noqa: SLF001
    assert menu.keybinds_tab.keys.buttons[PANIC].property("conflict") is True


def test_refresh_reloads_widgets(settings: Settings, signals: AppSignals, session: ProfileSession) -> None:
    menu = make(settings, signals, session)
    enable = next(b for b in menu.aimbot_tab.findChildren(QCheckBox) if b.text() == "Enable aimbot")
    assert not enable.isChecked()
    settings.aimbot.enabled = True  # changed outside the UI (e.g. by a hotkey)
    signals.refresh_requested.emit()
    assert enable.isChecked()


def test_status_pill(settings: Settings, signals: AppSignals, session: ProfileSession) -> None:
    menu = make(settings, signals, session)
    signals.status_changed.emit(ControllerStatus())
    assert "Not attached" in menu.status_pill.text()
    signals.status_changed.emit(ControllerStatus(attached=True, offsets_ok=True, entity_count=7, tick_rate=60))
    assert "7 bots" in menu.status_pill.text()


def test_keybinds_tab_badge_on_conflict(settings: Settings, signals: AppSignals, session: ProfileSession) -> None:
    menu = make(settings, signals, session)
    index = menu.tabs.indexOf(menu.keybinds_tab)
    assert menu.tabs.tabText(index) == "Keybinds"
    settings.keybinds.binds[PANIC].key = settings.keybinds.binds[AIMBOT_ACTIVATE].key
    signals.settings_changed.emit("keybinds")
    assert menu.tabs.tabText(index) == "Keybinds ⚠"


def test_player_tab_shows_game_fov(settings: Settings, signals: AppSignals, session: ProfileSession) -> None:
    menu = make(settings, signals, session)
    signals.status_changed.emit(ControllerStatus(attached=True, offsets_ok=True, game_fov=110.0))
    assert menu.player_tab.fov_now.text() == "110°"
