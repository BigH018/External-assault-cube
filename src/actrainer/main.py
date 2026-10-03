"""Entry point: DPI awareness -> QApplication -> load profile -> wire services -> start the tick loop."""

from __future__ import annotations

import logging
import sys

from PyQt5.QtWidgets import QApplication

from actrainer import __version__, config
from actrainer.app.controller import Controller
from actrainer.settings.signals import AppSignals
from actrainer.settings.store import ProfileStore
from actrainer.ui.menu_window import MenuWindow
from actrainer.ui.profile_session import ProfileSession
from actrainer.ui.theme import apply_theme
from actrainer.winapi import win32

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

log = logging.getLogger("actrainer")


def setup_logging() -> None:
    """Log to the console and to logs/actrainer.log (overwritten each run)."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.LOGS_DIR / config.LOG_FILE, mode="w", encoding="utf-8"))
    except OSError:
        pass  # console logging still works
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=handlers)


def main() -> int:
    setup_logging()
    log.info("AC Trainer %s starting (offline bot matches only)", __version__)
    # Must happen before QApplication exists, or the overlay will be offset on scaled displays.
    if not win32.set_dpi_aware():
        log.warning("could not enable DPI awareness; overlay may be offset on scaled displays")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # hiding the menu must not quit
    apply_theme(app)

    store = ProfileStore()
    profile_name, settings = store.load_startup()
    log.info("loaded profile '%s'", profile_name)

    signals = AppSignals()
    session = ProfileSession(store, settings, signals, profile_name)
    controller = Controller(settings, signals)
    menu = MenuWindow(settings, signals, session, lambda: controller.game_hwnd)

    def quit_app() -> None:
        log.info("quitting")
        controller.shutdown()
        menu.allow_close()
        menu.close()
        app.quit()

    signals.menu_toggle_requested.connect(menu.toggle)
    signals.quit_requested.connect(quit_app)

    controller.start()
    menu.show_menu()
    if store.last_warnings:
        log.warning("profile '%s' loaded with %d warning(s)", profile_name, len(store.last_warnings))
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
