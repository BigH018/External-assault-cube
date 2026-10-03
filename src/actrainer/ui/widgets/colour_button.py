"""Colour chip: a swatch (over a checkerboard) plus '#RRGGBB · 100%'. Click it to open the colour picker popup.

Changes apply live while the popup is open (colourChanged is emitted on every preview), and Cancel
restores the original colour, so you can see a new ESP colour on real bots before deciding.
"""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPaintEvent, QPainterPath, QPen
from PyQt5.QtWidgets import QPushButton, QWidget

from actrainer.ui import theme
from actrainer.ui.widgets.colour_picker import ColourPopup, describe, paint_checker, to_qcolor

SWATCH_SIZE = 18
SWATCH_LEFT = 10
CHIP_MIN_WIDTH = 150


class ColourButton(QPushButton):
    colourChanged = pyqtSignal(str)

    def __init__(self, rgba: str = "#FFFFFFFF", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("colourChip")
        self.setMinimumWidth(CHIP_MIN_WIDTH)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to choose a colour (presets, custom colour, opacity)")
        self._rgba = rgba
        self.popup: ColourPopup | None = None
        self._refresh()
        self.clicked.connect(self.open_picker)

    def colour(self) -> str:
        return self._rgba

    def setColour(self, rgba: str) -> None:  # noqa: N802 (Qt naming)
        """Set the colour without emitting colourChanged."""
        self._rgba = rgba
        self._refresh()

    def open_picker(self) -> None:
        original = self._rgba
        self.popup = ColourPopup(original, self)
        self.popup.colourPreview.connect(self._preview)
        self.popup.cancelled.connect(lambda: self._preview(original))
        self.popup.show_below(self)

    def _preview(self, rgba: str) -> None:
        if rgba != self._rgba:
            self._rgba = rgba
            self._refresh()
            self.colourChanged.emit(rgba)

    def _refresh(self) -> None:
        self.setText(describe(self._rgba))
        self.update()

    def paintEvent(self, e: QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(e)  # background, border and text (text is padded right of the swatch)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(SWATCH_LEFT, (self.height() - SWATCH_SIZE) / 2, SWATCH_SIZE, SWATCH_SIZE)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 4, 4)
        p.setClipPath(clip)
        paint_checker(p, rect)
        p.fillRect(rect, to_qcolor(self._rgba))
        p.setClipping(False)
        p.setPen(QPen(QColor(theme.TEXT_DIM), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, 4, 4)
        p.end()
