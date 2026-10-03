"""iOS-style toggle switch, plus a ToggleRow (label on the left, switch on the right).

ToggleSwitch is a checkable QAbstractButton, so it has the usual setChecked / isChecked / toggled API.
"""

from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, QVariantAnimation
from PyQt5.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PyQt5.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from actrainer.ui import theme

SWITCH_SIZE = QSize(40, 22)
KNOB_MARGIN = 3
ANIMATION_MS = 120


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(SWITCH_SIZE)
        self._position = 0.0  # 0 = off (knob left), 1 = on (knob right)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(ANIMATION_MS)
        self._animation.valueChanged.connect(self._on_animate)
        self.toggled.connect(self._start_animation)

    def setChecked(self, checked: bool) -> None:  # noqa: N802 (Qt naming)
        """Set the state; programmatic changes jump straight to the end position (no animation)."""
        super().setChecked(checked)
        self._animation.stop()
        self._position = 1.0 if checked else 0.0
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return SWITCH_SIZE

    def _start_animation(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def _on_animate(self, value: float) -> None:
        self._position = float(value)
        self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        off, on = QColor(theme.SWITCH_OFF), QColor(theme.ACCENT)
        t = self._position
        track = QColor(round(off.red() + (on.red() - off.red()) * t), round(off.green() + (on.green() - off.green()) * t),
                       round(off.blue() + (on.blue() - off.blue()) * t))
        if not self.isEnabled():
            track.setAlpha(110)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        radius = h / 2 - KNOB_MARGIN
        x = KNOB_MARGIN + radius + t * (w - 2 * (KNOB_MARGIN + radius))
        p.setBrush(QColor(theme.KNOB))
        p.drawEllipse(QPointF(x, h / 2), radius, radius)
        p.end()


class ToggleRow(QWidget):
    """[Label (+ optional description)] ........ [switch]. Clicking the label also toggles."""

    def __init__(self, text: str, description: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.switch = ToggleSwitch()
        self._label = QLabel(text)
        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(1)
        texts.addWidget(self._label)
        if description:
            desc = QLabel(description)
            desc.setObjectName("dim")
            desc.setWordWrap(True)
            texts.addWidget(desc)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.addLayout(texts, 1)
        layout.addWidget(self.switch, 0, Qt.AlignVCenter)
        self.setCursor(Qt.PointingHandCursor)

    def text(self) -> str:
        return self._label.text()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.switch.isEnabled():
            self.switch.toggle()
        super().mousePressEvent(event)
