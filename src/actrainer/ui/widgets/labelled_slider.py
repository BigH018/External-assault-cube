"""Slider with a name label and a live value readout. Supports floats via fixed decimal scaling."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

LABEL_MIN_WIDTH = 110


class LabelledSlider(QWidget):
    """[label] [------o------] [value suffix]

    QSlider only handles ints, so a float range is scaled by 10**decimals internally.
    """

    valueChanged = pyqtSignal(float)

    def __init__(self, label: str, minimum: float, maximum: float, decimals: int = 0,
                 suffix: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scale = 10 ** decimals
        self._decimals = decimals
        self._suffix = suffix

        self._name = QLabel(label)
        self._name.setMinimumWidth(LABEL_MIN_WIDTH)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(round(minimum * self._scale), round(maximum * self._scale))
        self._value = QLabel()
        self._value.setObjectName("value")
        self._value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._name)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._value)

        self._slider.valueChanged.connect(self._on_slider)
        self._update_label()

    def value(self) -> float:
        return self._slider.value() / self._scale

    def setValue(self, value: float) -> None:  # noqa: N802 (Qt naming)
        """Set the value without emitting valueChanged (used when loading settings)."""
        self._slider.blockSignals(True)
        self._slider.setValue(round(value * self._scale))
        self._slider.blockSignals(False)
        self._update_label()

    def _on_slider(self, _raw: int) -> None:
        self._update_label()
        self.valueChanged.emit(self.value())

    def _update_label(self) -> None:
        self._value.setText(f"{self.value():.{self._decimals}f}{self._suffix}")
