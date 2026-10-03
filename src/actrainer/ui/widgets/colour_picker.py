"""Dark colour picker popup: presets, saturation/value square, hue bar, opacity, hex, old/new preview.

Colours are exchanged as "#RRGGBBAA" strings (the settings format). Qt's own hex-with-alpha format is
"#AARRGGBB", so conversion is explicit.

Behaviour:
- Every change emits colourPreview(rgba) immediately, so the owner can apply it live (e.g. see the ESP colour change).
- Apply (or clicking outside) keeps the colour. Cancel / Escape emits cancelled() so the owner restores the original.
"""

from __future__ import annotations

import re

from PyQt5.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QKeyEvent, QLinearGradient, QMouseEvent, QPainter, QPaintEvent, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from actrainer.ui import theme

PRESETS = (
    "#FF4040", "#FF9F43", "#FFD93D", "#A3E635", "#34C759", "#2DD4BF",
    "#22D3EE", "#8EC9FF", "#4C8DFF", "#A78BFA", "#F472B6", "#FFFFFF",
)
SV_SIZE = (200, 150)
HUE_SIZE = (18, 150)
PREVIEW_SIZE = (44, 28)
CHECKER_CELL = 5
MARKER_RADIUS = 6
ALPHA_MAX = 255
PERCENT = 100
_HEX_RE = re.compile(r"^#?([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?$")


# --- conversions -------------------------------------------------------------------------

def to_qcolor(rgba: str) -> QColor:
    """'#RRGGBBAA' -> QColor."""
    r, g, b, a = (int(rgba[i:i + 2], 16) for i in (1, 3, 5, 7))
    return QColor(r, g, b, a)


def from_qcolor(colour: QColor) -> str:
    """QColor -> '#RRGGBBAA'."""
    return f"#{colour.red():02X}{colour.green():02X}{colour.blue():02X}{colour.alpha():02X}"


def parse_hex(text: str, alpha: int) -> str | None:
    """'#RRGGBB' / 'RRGGBB' (keeps `alpha`) or '#RRGGBBAA' -> '#RRGGBBAA', else None."""
    m = _HEX_RE.match(text.strip())
    if not m:
        return None
    return f"#{m.group(1).upper()}{(m.group(2) or f'{alpha:02X}').upper()}"


def describe(rgba: str) -> str:
    """Human-readable label, e.g. '#FF4040 · 100%'."""
    alpha = int(rgba[7:9], 16)
    return f"{rgba[:7]} · {round(alpha * PERCENT / ALPHA_MAX)}%"


def paint_checker(p: QPainter, rect: QRectF) -> None:
    """Grey checkerboard, the usual way to show that a colour is see-through."""
    p.save()
    p.setClipRect(rect)
    p.fillRect(rect, QColor("#CFCFCF"))
    cols = int(rect.width() // CHECKER_CELL) + 1
    rows = int(rect.height() // CHECKER_CELL) + 1
    for row in range(rows):
        for col in range(row % 2, cols, 2):
            p.fillRect(QRectF(rect.x() + col * CHECKER_CELL, rect.y() + row * CHECKER_CELL,
                              CHECKER_CELL, CHECKER_CELL), QColor("#9A9A9A"))
    p.restore()


# --- building blocks ----------------------------------------------------------------------

class SaturationValueSquare(QWidget):
    """Horizontal = saturation (white -> full colour), vertical = value (bright -> black)."""

    changed = pyqtSignal(float, float)  # saturation, value (0..1)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(*SV_SIZE)
        self.setCursor(Qt.CrossCursor)
        self.hue = 0.0
        self.sat = 1.0
        self.val = 1.0

    def set_hsv(self, h: float, s: float, v: float) -> None:
        self.hue, self.sat, self.val = h, s, v
        self.update()

    def paintEvent(self, _e: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        p.fillRect(r, QColor.fromHsvF(self.hue, 1.0, 1.0))
        white = QLinearGradient(r.topLeft(), r.topRight())
        white.setColorAt(0, QColor(255, 255, 255, 255))
        white.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(r, white)
        black = QLinearGradient(r.topLeft(), r.bottomLeft())
        black.setColorAt(0, QColor(0, 0, 0, 0))
        black.setColorAt(1, QColor(0, 0, 0, 255))
        p.fillRect(r, black)
        x, y = self.sat * (r.width() - 1), (1 - self.val) * (r.height() - 1)
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(x, y), MARKER_RADIUS, MARKER_RADIUS)
        p.setPen(QPen(QColor(0, 0, 0, 160), 1))
        p.drawEllipse(QPointF(x, y), MARKER_RADIUS + 1.5, MARKER_RADIUS + 1.5)
        p.end()

    def _pick(self, pos: QPoint) -> None:
        self.sat = min(1.0, max(0.0, pos.x() / (self.width() - 1)))
        self.val = min(1.0, max(0.0, 1 - pos.y() / (self.height() - 1)))
        self.update()
        self.changed.emit(self.sat, self.val)

    def mousePressEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        self._pick(e.pos())

    def mouseMoveEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        if e.buttons() & Qt.LeftButton:
            self._pick(e.pos())


class HueBar(QWidget):
    """Vertical rainbow; picks the hue (0..1)."""

    changed = pyqtSignal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(*HUE_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.hue = 0.0

    def set_hue(self, h: float) -> None:
        self.hue = h
        self.update()

    def paintEvent(self, _e: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        gradient = QLinearGradient(r.topLeft(), r.bottomLeft())
        steps = 6
        for i in range(steps + 1):
            gradient.setColorAt(i / steps, QColor.fromHsvF((i / steps) % 1.0, 1.0, 1.0))
        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawRoundedRect(r, 4, 4)
        y = self.hue * (r.height() - 1)
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(1, y - 3, r.width() - 2, 6), 2, 2)
        p.end()

    def _pick(self, pos: QPoint) -> None:
        self.hue = min(1.0, max(0.0, pos.y() / (self.height() - 1)))
        self.update()
        self.changed.emit(self.hue)

    def mousePressEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        self._pick(e.pos())

    def mouseMoveEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        if e.buttons() & Qt.LeftButton:
            self._pick(e.pos())


class ColourPreview(QWidget):
    """A swatch drawn over a checkerboard (so transparency is visible)."""

    def __init__(self, rgba: str) -> None:
        super().__init__()
        self.setFixedSize(*PREVIEW_SIZE)
        self.rgba = rgba

    def set_colour(self, rgba: str) -> None:
        self.rgba = rgba
        self.update()

    def paintEvent(self, _e: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        r = QRectF(self.rect())
        paint_checker(p, r)
        p.fillRect(r, to_qcolor(self.rgba))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawRect(r.adjusted(0, 0, -1, -1))
        p.end()


# --- popup ------------------------------------------------------------------------------------

class ColourPopup(QFrame):
    colourPreview = pyqtSignal(str)
    accepted = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, rgba: str, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("colourPopup")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.original = rgba
        colour = to_qcolor(rgba)
        h, s, v, _ = colour.getHsvF()
        self._h = max(0.0, h)  # Qt returns -1 hue for greys
        self._s, self._v = s, v
        self._alpha = colour.alpha()
        self._done = False

        presets = QGridLayout()
        presets.setSpacing(6)
        for i, hex6 in enumerate(PRESETS):
            swatch = QPushButton()
            swatch.setObjectName("swatch")
            swatch.setFixedSize(22, 22)
            swatch.setToolTip(hex6)
            swatch.setStyleSheet(f"background: {hex6};")  # data colour, not theme
            swatch.clicked.connect(lambda _c=False, h6=hex6: self._apply_preset(h6))
            presets.addWidget(swatch, 0, i)

        self.square = SaturationValueSquare()
        self.hue_bar = HueBar()
        self.square.changed.connect(self._on_sv)
        self.hue_bar.changed.connect(self._on_hue)
        picker = QHBoxLayout()
        picker.addWidget(self.square)
        picker.addWidget(self.hue_bar)
        picker.addStretch(1)

        self.alpha_slider = QSlider(Qt.Horizontal)
        self.alpha_slider.setRange(0, PERCENT)
        self.alpha_label = QLabel()
        self.alpha_label.setObjectName("value")
        self.alpha_slider.valueChanged.connect(self._on_alpha)
        opacity = QHBoxLayout()
        opacity.addWidget(QLabel("Opacity"))
        opacity.addWidget(self.alpha_slider, 1)
        opacity.addWidget(self.alpha_label)

        self.hex_edit = QLineEdit()
        self.hex_edit.setMaxLength(9)
        self.hex_edit.setFixedWidth(110)
        self.hex_edit.setToolTip("#RRGGBB or #RRGGBBAA")
        self.hex_edit.editingFinished.connect(self._on_hex)
        self.old_preview = ColourPreview(rgba)
        self.old_preview.setToolTip("Original colour (click to restore)")
        self.old_preview.mousePressEvent = lambda _e: self._set_rgba(self.original)  # type: ignore[assignment]
        self.new_preview = ColourPreview(rgba)
        values = QHBoxLayout()
        values.addWidget(QLabel("Hex"))
        values.addWidget(self.hex_edit)
        values.addStretch(1)
        values.addWidget(QLabel("Old"))
        values.addWidget(self.old_preview)
        values.addWidget(QLabel("New"))
        values.addWidget(self.new_preview)

        cancel = QPushButton("Cancel")
        apply = QPushButton("Apply")
        apply.setObjectName("primary")
        cancel.clicked.connect(self.cancel)
        apply.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(apply)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        title = QLabel("Presets")
        title.setObjectName("dim")
        layout.addWidget(title)
        layout.addLayout(presets)
        layout.addLayout(picker)
        layout.addLayout(opacity)
        layout.addLayout(values)
        layout.addLayout(buttons)
        self._sync_widgets()

    # --- state ---------------------------------------------------------------------------

    def current(self) -> str:
        c = QColor.fromHsvF(self._h, self._s, self._v)
        c.setAlpha(self._alpha)
        return from_qcolor(c)

    def _set_rgba(self, rgba: str) -> None:
        colour = to_qcolor(rgba)
        h, s, v, _ = colour.getHsvF()
        if h >= 0:
            self._h = h  # keep the previous hue for greys/white/black
        self._s, self._v, self._alpha = s, v, colour.alpha()
        self._changed()

    def _apply_preset(self, hex6: str) -> None:
        self._set_rgba(f"{hex6}{self._alpha:02X}")  # presets keep the current opacity

    def _on_sv(self, s: float, v: float) -> None:
        self._s, self._v = s, v
        self._changed()

    def _on_hue(self, h: float) -> None:
        self._h = h
        self._changed()

    def _on_alpha(self, percent: int) -> None:
        self._alpha = round(percent * ALPHA_MAX / PERCENT)
        self._changed(update_slider=False)

    def _on_hex(self) -> None:
        parsed = parse_hex(self.hex_edit.text(), self._alpha)
        if parsed is None:
            self.hex_edit.setText(self.current())  # reject: show the valid current value again
            return
        self._set_rgba(parsed)

    def _changed(self, update_slider: bool = True) -> None:
        self._sync_widgets(update_slider)
        self.colourPreview.emit(self.current())

    def _sync_widgets(self, update_slider: bool = True) -> None:
        rgba = self.current()
        self.square.set_hsv(self._h, self._s, self._v)
        self.hue_bar.set_hue(self._h)
        if update_slider:
            self.alpha_slider.blockSignals(True)
            self.alpha_slider.setValue(round(self._alpha * PERCENT / ALPHA_MAX))
            self.alpha_slider.blockSignals(False)
        self.alpha_label.setText(f"{round(self._alpha * PERCENT / ALPHA_MAX)}%")
        if not self.hex_edit.hasFocus():
            self.hex_edit.setText(rgba)
        self.new_preview.set_colour(rgba)

    # --- closing ----------------------------------------------------------------------------

    def accept(self) -> None:
        self._done = True
        self.accepted.emit(self.current())
        self.close()

    def cancel(self) -> None:
        self._done = True
        self.cancelled.emit()
        self.close()

    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        if e.key() == Qt.Key_Escape:
            self.cancel()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter) and not self.hex_edit.hasFocus():
            self.accept()
        else:
            super().keyPressEvent(e)

    def hideEvent(self, e) -> None:  # noqa: ANN001, N802
        # Clicking outside closes a Qt.Popup: treat it as "keep" (the colour is already applied live).
        if not self._done:
            self._done = True
            self.accepted.emit(self.current())
        super().hideEvent(e)

    def show_below(self, anchor: QWidget) -> None:
        """Open just below `anchor`, kept inside the screen."""
        self.adjustSize()
        pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 4))
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        x = min(max(area.left(), pos.x()), area.right() - self.width())
        y = pos.y() if pos.y() + self.height() <= area.bottom() else anchor.mapToGlobal(QPoint(0, 0)).y() - self.height() - 4
        self.move(x, y)
        self.show()
