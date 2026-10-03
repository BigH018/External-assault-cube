"""Tests for overlay/painter.py (render to an image) and overlay/window.py (offscreen)."""

from __future__ import annotations

from PyQt5.QtGui import QColor, QImage, QPainter

from actrainer.features.primitives import Circle, FilledRect, Line, OverlayFrame, Rect, Text
from actrainer.overlay.painter import paint, qcolor
from actrainer.overlay.window import OverlayWindow
from actrainer.settings.models import Settings


def render(primitives: list, w: int = 100, h: int = 100) -> QImage:
    image = QImage(w, h, QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    paint(painter, primitives)
    painter.end()
    return image


def test_qcolor_parses_rgba() -> None:
    c = qcolor("#11223344")
    assert (c.red(), c.green(), c.blue(), c.alpha()) == (0x11, 0x22, 0x33, 0x44)


def test_paints_each_primitive_where_expected(qapp) -> None:  # noqa: ANN001
    image = render([
        FilledRect(10, 10, 10, 10, "#FF0000FF"),
        Line(0, 50, 99, 50, "#00FF00FF", 3),
        Rect(60, 60, 30, 30, "#0000FFFF", 3),
        Circle(30, 80, 10, "#FFFF00FF", 3),
        Text(50, 2, "hi", "#FFFFFFFF", 12),
    ])
    assert image.pixelColor(15, 15) == QColor(255, 0, 0, 255)          # filled rect
    assert image.pixelColor(30, 50).green() == 255                       # line
    assert image.pixelColor(60, 75).blue() == 255                        # rect left edge
    assert image.pixelColor(75, 75).alpha() == 0                         # rect interior stays transparent
    assert image.pixelColor(20, 80).red() > 200                          # circle left edge
    assert image.pixelColor(30, 80).alpha() == 0                         # circle centre transparent
    assert any(image.pixelColor(x, y).alpha() > 0 for x in range(40, 60) for y in range(2, 16))  # text drawn


def test_window_follows_frames(qapp) -> None:  # noqa: ANN001
    window = OverlayWindow(Settings())
    window.show_frame(OverlayFrame(True, 10, 20, 640, 480, (Line(0, 0, 10, 10, "#FFFFFFFF"),)))
    assert window.isVisible()
    assert (window.x(), window.y(), window.width(), window.height()) == (10, 20, 640, 480)
    window.show_frame(OverlayFrame(visible=False))
    assert not window.isVisible()
    window.close()


def test_window_repaint_rate_follows_settings(qapp) -> None:  # noqa: ANN001
    settings = Settings()
    window = OverlayWindow(settings)
    settings.general.overlay_fps = 120
    window.apply_fps()
    assert window._repaint_timer.interval() == 8  # noqa: SLF001 - round(1000/120)
    window.close()
