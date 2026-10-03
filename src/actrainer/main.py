"""Entry point: DPI awareness -> QApplication -> load profile -> wire services -> start the tick loop."""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path
from types import TracebackType

from PyQt5.QtCore import QLockFile
from PyQt5.QtWidgets import QApplication, QMessageBox

from actrainer import __version__, config
from actrainer.app.controller import Controller
from actrainer.overlay.window import OverlayWindow
from actrainer.settings.signals import AppSignals
from actrainer.settings.store import ProfileStore
from actrainer.ui.menu_window import MenuWindow
from actrainer.ui.profile_session import ProfileSession
from actrainer.ui.theme import apply_theme
from actrainer.winapi import win32

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

log = logging.getLogger("actrainer")


def setup_logging() -> None:
    """Console logging. The log file is added by add_file_logging() once we hold the single-instance lock."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=[logging.StreamHandler()])


def add_file_logging() -> None:
    """Also log to logs/actrainer.log (overwritten each run).

    Only called after the single-instance lock is acquired, so a second copy that's about to exit can't
    wipe the running trainer's log.
    """
    try:
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(config.LOGS_DIR / config.LOG_FILE, mode="w", encoding="utf-8")
    except OSError:
        return  # console logging still works
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(handler)


def log_unhandled(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
    """Log exceptions instead of letting PyQt5 abort the whole app.

    Since PyQt 5.5, an unhandled Python exception inside a Qt callback (slot, paintEvent, ...) calls
    qFatal() and kills the process. With this hook it's logged with a traceback and the app keeps running.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    log.critical("unhandled exception", exc_info=(exc_type, exc, tb))


def acquire_single_instance_lock() -> QLockFile | None:
    """Lock file in the temp dir. Returns None if another trainer is already running."""
    lock = QLockFile(str(Path(tempfile.gettempdir()) / config.LOCK_FILE_NAME))
    lock.setStaleLockTime(0)  # a crashed instance's lock is detected via its PID instead of by age
    return lock if lock.tryLock(config.LOCK_TIMEOUT_MS) else None


def main() -> int:
    setup_logging()
    sys.excepthook = log_unhandled
    # Must happen before QApplication exists, or the overlay will be offset on scaled displays.
    if not win32.set_dpi_aware():
        log.warning("could not enable DPI awareness; overlay may be offset on scaled displays")
    win32.set_app_user_model_id(config.APP_USER_MODEL_ID)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # hiding the menu must not quit
    apply_theme(app)

    lock = acquire_single_instance_lock()
    if lock is None:
        log.error("another copy is already running")
        QMessageBox.warning(None, config.MENU_TITLE, f"{config.APP_NAME} is already running.\n"
                            "Use its menu hotkey (default INSERT) or close it first.")
        return 1
    add_file_logging()
    log.info("%s %s running (offline bot matches only)", config.MENU_TITLE, __version__)

    store = ProfileStore()
    profile_name, settings = store.load_startup()
    log.info("loaded profile '%s'", profile_name)

    signals = AppSignals()
    session = ProfileSession(store, settings, signals, profile_name)
    controller = Controller(settings, signals)
    menu = MenuWindow(settings, signals, session, lambda: controller.game_hwnd)
    overlay = OverlayWindow(settings)
    signals.overlay_frame.connect(overlay.show_frame)
    signals.settings_changed.connect(lambda section: overlay.apply_fps() if section == "general" else None)
    signals.refresh_requested.connect(overlay.apply_fps)  # profile load / reset may change overlay FPS

    def quit_app() -> None:
        log.info("quitting")
        controller.shutdown()
        overlay.close()
        menu.allow_close()
        menu.close()
        app.quit()

    signals.menu_toggle_requested.connect(menu.toggle)
    signals.quit_requested.connect(quit_app)

    controller.start()
    menu.show_menu()
    if store.last_warnings:
        log.warning("profile '%s' loaded with %d warning(s)", profile_name, len(store.last_warnings))
        QMessageBox.information(menu, "Profile loaded with warnings",
                                f"Some settings in '{profile_name}' were invalid and were reset or adjusted:\n\n• "
                                + "\n• ".join(store.last_warnings))
    code = app.exec_()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())
