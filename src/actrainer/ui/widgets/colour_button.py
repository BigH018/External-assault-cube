"""Button showing a colour swatch. Clicking opens a colour picker with alpha.

Colours are exchanged as "#RRGGBBAA" strings (the settings format). Note Qt's own hex format with
alpha is "#AARRGGBB", so we convert explicitly.
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QColorDialog, QPushButton, QWidget

from actrainer.ui import theme

SWATCH_SIZE = (44, 22)


def to_qcolor(rgba: str) -> QColor:
    """'#RRGGBBAA' -> QColor."""
    r, g, b, a = (int(rgba[i:i + 2], 16) for i in (1, 3, 5, 7))
    return QColor(r, g, b, a)


def from_qcolor(colour: QColor) -> str:
    """QColor -> '#RRGGBBAA'."""
    return f"#{colour.red():02X}{colour.green():02X}{colour.blue():02X}{colour.alpha():02X}"


class ColourButton(QPushButton):
    colourChanged = pyqtSignal(str)

    def __init__(self, rgba: str = "#FFFFFFFF", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(*SWATCH_SIZE)
        self.setToolTip("Click to choose a colour (with transparency)")
        self._rgba = rgba
        self._paint()
        self.clicked.connect(self._pick)

    def colour(self) -> str:
        return self._rgba

    def setColour(self, rgba: str) -> None:  # noqa: N802 (Qt naming)
        """Set the colour without emitting colourChanged."""
        self._rgba = rgba
        self._paint()

    def _pick(self) -> None:
        chosen = QColorDialog.getColor(to_qcolor(self._rgba), self, "Choose colour",
                                       QColorDialog.ShowAlphaChannel)
        if chosen.isValid():
            self._rgba = from_qcolor(chosen)
            self._paint()
            self.colourChanged.emit(self._rgba)

    def _paint(self) -> None:
        c = to_qcolor(self._rgba)
        # The swatch is the one place a colour comes from data, not the theme.
        self.setStyleSheet(f"background: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});"
                           f"border: 1px solid {theme.TEXT_DIM}; border-radius: 4px;")
