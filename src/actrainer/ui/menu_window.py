"""Main menu window: header with status + Quit, and the five tabs.

Behaviour (CLAUDE.md §9 "Menu window behaviour"):
- toggle() shows/hides. Shown = always on top, raised and forced to the foreground (so the game
  releases the mouse), centred over the game window the first time, then at its remembered position.
- Hidden = fully hidden; focus goes back to the game window.
- The close button asks Quit / Hide / Cancel. The Quit button quits (with an unsaved-changes warning).
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget

from actrainer import config
from actrainer.app.status import ControllerStatus
from actrainer.input.keybinds import find_conflicts
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.ui.layout import row
from actrainer.ui.profile_session import ProfileSession
from actrainer.ui.tabs.aimbot_tab import AimbotTab
from actrainer.ui.tabs.esp_tab import EspTab
from actrainer.ui.tabs.keybinds_tab import KeybindsTab
from actrainer.ui.tabs.player_tab import PlayerTab
from actrainer.ui.tabs.settings_tab import SettingsTab
from actrainer.ui.theme import restyle
from actrainer.winapi import win32

log = logging.getLogger(__name__)


class MenuWindow(QWidget):
    def __init__(self, settings: Settings, signals: AppSignals, session: ProfileSession,
                 game_hwnd: Callable[[], int | None]) -> None:
        super().__init__(None, Qt.Window | Qt.WindowStaysOnTopHint)
        self.settings = settings
        self.signals = signals
        self.session = session
        self._game_hwnd = game_hwnd
        self._allow_close = False
        self.resize(*config.MENU_SIZE)

        title = QLabel(config.MENU_TITLE)
        title.setObjectName("title")
        self.status_pill = QLabel()
        self.status_pill.setObjectName("status")
        quit_button = QPushButton("Quit")
        quit_button.setObjectName("danger")
        quit_button.clicked.connect(self.request_quit)

        self.tabs = QTabWidget()
        self.aimbot_tab = AimbotTab(settings, signals)
        self.esp_tab = EspTab(settings, signals)
        self.player_tab = PlayerTab(settings, signals)
        self.keybinds_tab = KeybindsTab(settings, signals)
        self.settings_tab = SettingsTab(settings, signals, session)
        for tab, name in ((self.aimbot_tab, "Aimbot"), (self.esp_tab, "ESP"), (self.player_tab, "Player"),
                          (self.keybinds_tab, "Keybinds"), (self.settings_tab, "Settings")):
            self.tabs.addTab(tab, name)

        layout = QVBoxLayout(self)
        layout.addWidget(row(title, None, self.status_pill, quit_button))
        layout.addWidget(self.tabs, 1)

        signals.refresh_requested.connect(self.reload_all)
        signals.settings_changed.connect(self._on_settings_changed)
        signals.status_changed.connect(self.show_status)
        session.state_changed.connect(self._update_title)
        self._update_title()
        self._update_keybinds_badge()
        self.show_status(ControllerStatus())

    # --- tabs -------------------------------------------------------------------------

    def all_tabs(self) -> list[QWidget]:
        return [self.aimbot_tab, self.esp_tab, self.player_tab, self.keybinds_tab, self.settings_tab]

    def reload_all(self) -> None:
        """Refresh every control from settings (after a profile load, panic, hotkey...)."""
        for tab in self.all_tabs():
            tab.load_from_settings()  # type: ignore[attr-defined]
        self._update_keybinds_badge()

    def _on_settings_changed(self, section: str) -> None:
        # A bind can be shown on several tabs (e.g. aimbot key on Aimbot + Keybinds): keep them in sync.
        if section == "keybinds":
            self.reload_all()

    def _update_keybinds_badge(self) -> None:
        """Show ⚠ on the Keybinds tab when any key is bound to several actions."""
        index = self.tabs.indexOf(self.keybinds_tab)
        conflicts = find_conflicts(self.settings.keybinds.binds)
        self.tabs.setTabText(index, "Keybinds ⚠" if conflicts else "Keybinds")

    def _update_title(self) -> None:
        marker = " *" if self.session.dirty else ""
        self.setWindowTitle(f"{config.MENU_TITLE} — {self.session.current}{marker}")

    def show_status(self, status: ControllerStatus) -> None:
        if not status.attached:
            text, state = "● Not attached", "bad"
        elif not status.offsets_ok:
            text, state = "● Attached · not in a match", "warn"
        else:
            text, state = f"● Attached · {status.entity_count} bots · {status.tick_rate:.0f} Hz", "ok"
        self.status_pill.setText(text)
        self.status_pill.setProperty("state", state)
        restyle(self.status_pill)
        self.settings_tab.show_status(status)
        self.player_tab.show_status(status)

    # --- show / hide ---------------------------------------------------------------------

    def toggle(self) -> None:
        if self.isVisible():
            self.hide_menu()
        else:
            self.show_menu()

    def show_menu(self) -> None:
        self._place()
        self.show()
        self.raise_()
        self.activateWindow()
        # Qt's activateWindow alone is usually blocked by Windows' foreground lock while the game is focused.
        if not win32.force_foreground(int(self.winId())):
            log.info("menu could not take the foreground; press Esc in-game to free the cursor")

    def hide_menu(self) -> None:
        self._remember_position()
        self.hide()
        hwnd = self._game_hwnd()
        if hwnd:
            win32.force_foreground(hwnd)

    def _place(self) -> None:
        """Remembered position, or centred over the game window (else the screen) the first time."""
        pos = self.settings.general.menu_pos
        if pos is not None and self._on_some_screen(QPoint(*pos)):
            self.move(*pos)
            return
        hwnd = self._game_hwnd()
        rect = win32.get_window_rect(hwnd) if hwnd else None
        if rect is None:
            screen = QApplication.primaryScreen().availableGeometry()
            rect = (screen.x(), screen.y(), screen.width(), screen.height())
        x, y, w, h = rect
        self.move(x + (w - self.width()) // 2, y + (h - self.height()) // 2)

    @staticmethod
    def _on_some_screen(point: QPoint) -> bool:
        return any(s.availableGeometry().contains(point) for s in QApplication.screens())

    def _remember_position(self) -> None:
        # Not a user "edit": doesn't mark the profile dirty, but is saved with the next Save.
        self.settings.general.menu_pos = (self.x(), self.y())

    # --- quitting -----------------------------------------------------------------------------

    def request_quit(self) -> None:
        if self.session.dirty:
            answer = QMessageBox.question(self, "Unsaved changes",
                                          f"Profile '{self.session.current}' has unsaved changes. Quit anyway?")
            if answer != QMessageBox.Yes:
                return
        self.signals.quit_requested.emit()

    def allow_close(self) -> None:
        """Let the window close without the quit/hide prompt (used during shutdown)."""
        self._allow_close = True

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt naming)
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        box = QMessageBox(self)
        box.setWindowTitle("Close menu")
        box.setText("Quit the trainer, or just hide the menu?")
        box.setInformativeText("Hidden: press the menu hotkey to bring it back.")
        quit_button = box.addButton("Quit trainer", QMessageBox.DestructiveRole)
        hide_button = box.addButton("Hide menu", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(hide_button)
        box.exec_()
        if box.clickedButton() is quit_button:
            self.request_quit()
        elif box.clickedButton() is hide_button:
            self.hide_menu()
