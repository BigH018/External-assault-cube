"""Segmented control: a row of joined buttons where exactly one is selected (e.g. Head | Body)."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QWidget):
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, labels: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.buttons: list[QPushButton] = []
        for i, label in enumerate(labels):
            button = QPushButton(label)
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setProperty("first", i == 0)
            button.setProperty("last", i == len(labels) - 1)
            self._group.addButton(button, i)
            layout.addWidget(button)
            self.buttons.append(button)
        layout.addStretch(1)
        if self.buttons:
            self.buttons[0].setChecked(True)
        self._group.idClicked.connect(self.currentIndexChanged.emit)

    def currentIndex(self) -> int:  # noqa: N802 (Qt naming)
        return self._group.checkedId()

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        """Select a segment without emitting currentIndexChanged."""
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)
