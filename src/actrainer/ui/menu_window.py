"""Main menu window: header (title, status, logo), sidebar navigation and one page per section.

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
from PyQt5.QtGui import QCloseEvent, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from actrainer import __version__, config
from actrainer.app.status import ControllerStatus
from actrainer.input.actions import MENU_TOGGLE
from actrainer.input.keybinds import find_conflicts
from actrainer.input.keys import key_name
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.ui import theme
from actrainer.ui.profile_session import ProfileSession
from actrainer.ui.tabs import aimbot_tab, esp_tab, keybinds_tab, player_tab, settings_tab
from actrainer.ui.theme import restyle
from actrainer.winapi import win32

log = logging.getLogger(__name__)

# Sidebar glyphs (rendered from Segoe UI Symbol via Qt's font fallback).
NAV_GLYPHS = {"Aimbot": "◎", "ESP": "▣", "Player": "♥", "Keybinds": "⌨", "Settings": "⚙"}
NAV_SEPARATOR = "   "
CONFLICT_BADGE = "  ⚠"
PAGE_MARGIN = 20


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
        if theme.LOGO_PNG.is_file():
            self.setWindowIcon(QIcon(str(theme.LOGO_PNG)))

        self.aimbot_tab = aimbot_tab.AimbotTab(settings, signals)
        self.esp_tab = esp_tab.EspTab(settings, signals)
        self.player_tab = player_tab.PlayerTab(settings, signals)
        self.keybinds_tab = keybinds_tab.KeybindsTab(settings, signals)
        self.settings_tab = settings_tab.SettingsTab(settings, signals, session)
        sections = [(aimbot_tab, self.aimbot_tab), (esp_tab, self.esp_tab), (player_tab, self.player_tab),
                    (keybinds_tab, self.keybinds_tab), (settings_tab, self.settings_tab)]

        # --- pages + sidebar ---
        self.pages = QStackedWidget()
        self.nav_buttons: dict[QWidget, QPushButton] = {}
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(config.SIDEBAR_WIDTH)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(10, 14, 10, 14)
        side.setSpacing(4)
        for module, tab in sections:
            index = self.pages.addWidget(self._page(module.TITLE, module.SUBTITLE, tab))
            button = QPushButton(f"{NAV_GLYPHS[module.TITLE]}{NAV_SEPARATOR}{module.TITLE}")
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _c=False, i=index: self.pages.setCurrentIndex(i))
            self._nav_group.addButton(button, index)
            self.nav_buttons[tab] = button
            side.addWidget(button)
        self.nav_buttons[self.aimbot_tab].setChecked(True)
        side.addStretch(1)
        self.hotkey_hint = QLabel()
        self.hotkey_hint.setObjectName("dim")
        self.hotkey_hint.setWordWrap(True)
        side.addWidget(self.hotkey_hint)
        quit_button = QPushButton("⏻   Quit")
        quit_button.setObjectName("danger")
        quit_button.setCursor(Qt.PointingHandCursor)
        quit_button.clicked.connect(self.request_quit)
        side.addWidget(quit_button)
        version = QLabel(f"v{__version__} · offline bots only")
        version.setObjectName("dim")
        side.addWidget(version)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(sidebar)
        body.addWidget(self.pages, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._header())
        root.addLayout(body, 1)

        signals.refresh_requested.connect(self.reload_all)
        signals.settings_changed.connect(self._on_settings_changed)
        signals.status_changed.connect(self.show_status)
        session.state_changed.connect(self._update_title)
        self._update_title()
        self._update_keybinds_badge()
        self._update_hotkey_hint()
        self.show_status(ControllerStatus())

    # --- construction helpers ---------------------------------------------------------------

    def _header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        title = QLabel(config.APP_NAME)
        title.setObjectName("appTitle")
        subtitle = QLabel(config.APP_AUTHOR)
        subtitle.setObjectName("appSubtitle")
        self.status_pill = QLabel()
        self.status_pill.setObjectName("pill")
        self.logo = QLabel()
        self.logo.setToolTip(config.MENU_TITLE)
        if theme.LOGO_PNG.is_file():
            pixmap = QPixmap(str(theme.LOGO_PNG))  # 256 px source, smoothly scaled down
            self.logo.setPixmap(pixmap.scaled(config.LOGO_SIZE, config.LOGO_SIZE, Qt.KeepAspectRatio,
                                              Qt.SmoothTransformation))
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 10, 14, 10)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle, 0, Qt.AlignBottom)
        layout.addStretch(1)
        layout.addWidget(self.status_pill)
        layout.addWidget(self.logo)
        return header

    @staticmethod
    def _page(title: str, subtitle: str, content: QWidget) -> QWidget:
        """Page = title + subtitle above a scroll area holding the section's widget."""
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("pageSubtitle")
        sub.setWordWrap(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(PAGE_MARGIN, 0, PAGE_MARGIN, PAGE_MARGIN)
        inner_layout.addWidget(content)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, PAGE_MARGIN - 4, 0, 0)
        layout.setSpacing(4)
        head = QVBoxLayout()
        head.setContentsMargins(PAGE_MARGIN, 0, PAGE_MARGIN, 8)
        head.setSpacing(2)
        head.addWidget(heading)
        head.addWidget(sub)
        layout.addLayout(head)
        layout.addWidget(scroll, 1)
        return page

    # --- pages ---------------------------------------------------------------------------------

    def all_tabs(self) -> list[QWidget]:
        return [self.aimbot_tab, self.esp_tab, self.player_tab, self.keybinds_tab, self.settings_tab]

    def page_titles(self) -> list[str]:
        """Sidebar labels without glyphs or badges, in order."""
        return [b.text().split(NAV_SEPARATOR, 1)[1].replace(CONFLICT_BADGE, "") for b in self.nav_buttons.values()]

    def show_page(self, tab: QWidget) -> None:
        self.nav_buttons[tab].click()

    def current_tab(self) -> QWidget:
        return self.all_tabs()[self.pages.currentIndex()]

    def reload_all(self) -> None:
        """Refresh every control from settings (after a profile load, panic, hotkey...)."""
        for tab in self.all_tabs():
            tab.load_from_settings()  # type: ignore[attr-defined]
        self._update_keybinds_badge()
        self._update_hotkey_hint()

    def _on_settings_changed(self, section: str) -> None:
        # A bind can be shown on several pages (e.g. aimbot key on Aimbot + Keybinds): keep them in sync.
        if section == "keybinds":
            self.reload_all()

    def _update_keybinds_badge(self) -> None:
        """Show ⚠ on the Keybinds nav entry when any key is bound to several actions."""
        base = f"{NAV_GLYPHS['Keybinds']}{NAV_SEPARATOR}Keybinds"
        conflicts = find_conflicts(self.settings.keybinds.binds)
        self.nav_buttons[self.keybinds_tab].setText(base + (CONFLICT_BADGE if conflicts else ""))

    def _update_hotkey_hint(self) -> None:
        key = self.settings.keybinds.binds[MENU_TOGGLE].key
        self.hotkey_hint.setText(f"{key_name(key)} shows / hides this menu" if key is not None
                                 else "Menu hotkey is unbound")

    def _update_title(self) -> None:
        marker = " *" if self.session.dirty else ""
        self.setWindowTitle(f"{config.MENU_TITLE}  ·  {self.session.current}{marker}")

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
        box.setText(f"Quit {config.APP_NAME}, or just hide the menu?")
        box.setInformativeText("Hidden: press the menu hotkey to bring it back.")
        quit_button = box.addButton("Quit", QMessageBox.DestructiveRole)
        hide_button = box.addButton("Hide menu", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(hide_button)
        box.exec_()
        if box.clickedButton() is quit_button:
            self.request_quit()
        elif box.clickedButton() is hide_button:
            self.hide_menu()
