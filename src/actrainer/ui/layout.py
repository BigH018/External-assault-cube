"""Small layout helpers shared by the pages (cards, rows, labelled rows, hint text)."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

SPACING = 8


def group(title: str, grid: bool = False) -> tuple[QGroupBox, QVBoxLayout | QGridLayout]:
    """A titled group box and its layout (vertical by default, or a grid)."""
    box = QGroupBox(title)
    layout: QVBoxLayout | QGridLayout = QGridLayout(box) if grid else QVBoxLayout(box)
    layout.setSpacing(SPACING)
    return box, layout


def row(*widgets: QWidget | None, stretch_last: bool = False) -> QWidget:
    """Widgets side by side. None inserts a stretch."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACING)
    for w in widgets:
        if w is None:
            layout.addStretch(1)
        else:
            layout.addWidget(w)
    if stretch_last:
        layout.addStretch(1)
    return container


LABEL_WIDTH = 120


def labelled(text: str, widget: QWidget, label_width: int = LABEL_WIDTH) -> QWidget:
    """[label] [widget] on one line, label at a fixed width so rows line up."""
    label = QLabel(text)
    label.setMinimumWidth(label_width)
    return row(label, widget, stretch_last=True)


def hint(text: str) -> QLabel:
    """Dimmed explanatory text."""
    label = QLabel(text)
    label.setObjectName("dim")
    label.setWordWrap(True)
    return label
