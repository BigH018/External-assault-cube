"""Draws a list of primitives with QPainter. Knows nothing about players or settings."""

from __future__ import annotations

from collections.abc import Iterable

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen

from actrainer.features.primitives import Circle, FilledRect, Line, Primitive, Rect, Text, TextAlign

TEXT_FONT_FAMILY = "Segoe UI"
SHADOW_COLOUR = QColor(0, 0, 0, 200)
SHADOW_OFFSET = 1.0

_colour_cache: dict[str, QColor] = {}


def qcolor(rgba: str) -> QColor:
    """'#RRGGBBAA' -> QColor (cached: the same few colours are used thousands of times a second)."""
    colour = _colour_cache.get(rgba)
    if colour is None:
        r, g, b, a = (int(rgba[i:i + 2], 16) for i in (1, 3, 5, 7))
        colour = _colour_cache[rgba] = QColor(r, g, b, a)
    return colour


def _pen(rgba: str, thickness: float) -> QPen:
    pen = QPen(qcolor(rgba))
    pen.setWidthF(thickness)
    return pen


def paint(painter: QPainter, primitives: Iterable[Primitive]) -> None:
    """Draw every primitive in order (later ones on top)."""
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    fonts: dict[int, QFont] = {}
    for p in primitives:
        if isinstance(p, Line):
            painter.setPen(_pen(p.colour, p.thickness))
            painter.drawLine(QPointF(p.x1, p.y1), QPointF(p.x2, p.y2))
        elif isinstance(p, Rect):
            painter.setPen(_pen(p.colour, p.thickness))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(p.x, p.y, p.w, p.h))
        elif isinstance(p, FilledRect):
            painter.fillRect(QRectF(p.x, p.y, p.w, p.h), qcolor(p.colour))
        elif isinstance(p, Circle):
            painter.setPen(_pen(p.colour, p.thickness))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(p.cx, p.cy), p.radius, p.radius)
        elif isinstance(p, Text):
            font = fonts.get(p.size_px)
            if font is None:
                font = fonts[p.size_px] = QFont(TEXT_FONT_FAMILY)
                font.setPixelSize(p.size_px)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            width = metrics.horizontalAdvance(p.text)
            x = p.x - width / 2 if p.align is TextAlign.CENTRE else p.x
            baseline = p.y + metrics.ascent()
            painter.setPen(SHADOW_COLOUR)  # shadow first, so the text stays readable on bright backgrounds
            painter.drawText(QPointF(x + SHADOW_OFFSET, baseline + SHADOW_OFFSET), p.text)
            painter.setPen(qcolor(p.colour))
            painter.drawText(QPointF(x, baseline), p.text)
