"""Transparent, click-through, always-on-top window covering the game's client area.

The controller sends an OverlayFrame each tick (position/size + primitives + visible flag) via
AppSignals.overlay_frame. The window follows the game's client rect and repaints at most
settings.general.overlay_fps times per second, independently of the tick rate.
"""

from __future__ import annotations

import logging

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QGuiApplication, QPainter, QPaintEvent
from PyQt5.QtWidgets import QWidget

from actrainer.features.primitives import OverlayFrame
from actrainer.overlay.painter import paint
from actrainer.settings.models import Settings
from actrainer.winapi import win32

log = logging.getLogger(__name__)

MS_PER_SECOND = 1000
WINDOWS_PLATFORM = "windows"


class OverlayWindow(QWidget):
    def __init__(self, settings: Settings) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground)       # per-pixel alpha: only drawn pixels are visible
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)        # showing must never steal focus from the game
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._frame = OverlayFrame()
        self._dirty = False
        self._styled = False

        self._repaint_timer = QTimer(self)
        self._repaint_timer.timeout.connect(self._maybe_repaint)
        self.apply_fps()

    def apply_fps(self) -> None:
        """Update the repaint interval from settings.general.overlay_fps."""
        self._repaint_timer.start(max(1, round(MS_PER_SECOND / self.settings.general.overlay_fps)))

    def show_frame(self, frame: OverlayFrame) -> None:
        """Receive the latest frame (called every tick; painting happens on the repaint timer)."""
        if not frame.visible:
            if self.isVisible():
                self.hide()
            self._frame = frame
            return
        if (frame.x, frame.y, frame.width, frame.height) != (self.x(), self.y(), self.width(), self.height()):
            self.setGeometry(frame.x, frame.y, frame.width, frame.height)  # follow the game's client area
        if not self.isVisible():
            self.show()
            self._make_click_through()
        self._frame = frame
        self._dirty = True

    def _make_click_through(self) -> None:
        """Apply the Win32 click-through styles once the native window exists (real Windows platform only)."""
        if self._styled or QGuiApplication.platformName() != WINDOWS_PLATFORM:
            return
        win32.make_click_through(int(self.winId()))
        self._styled = True

    def _maybe_repaint(self) -> None:
        if self._dirty and self.isVisible():
            self._dirty = False
            self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        try:
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(self.rect(), Qt.transparent)  # clear last frame to fully transparent
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            paint(painter, self._frame.primitives)
        finally:
            painter.end()
