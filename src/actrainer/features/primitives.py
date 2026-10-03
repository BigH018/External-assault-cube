"""Pure draw primitives. ESP produces a list of these; the overlay painter knows how to draw them.

Coordinates are pixels relative to the game's client area (top-left = 0, 0).
Colours are "#RRGGBBAA" strings, like the settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TextAlign(str, Enum):
    CENTRE = "centre"   # x is the horizontal centre of the text
    LEFT = "left"       # x is the left edge


@dataclass(frozen=True, slots=True)
class Line:
    x1: float
    y1: float
    x2: float
    y2: float
    colour: str
    thickness: float = 1.0


@dataclass(frozen=True, slots=True)
class Rect:
    """Outline rectangle."""

    x: float
    y: float
    w: float
    h: float
    colour: str
    thickness: float = 1.0


@dataclass(frozen=True, slots=True)
class FilledRect:
    x: float
    y: float
    w: float
    h: float
    colour: str


@dataclass(frozen=True, slots=True)
class Circle:
    """Outline circle."""

    cx: float
    cy: float
    radius: float
    colour: str
    thickness: float = 1.0


@dataclass(frozen=True, slots=True)
class Text:
    """Text whose TOP sits at y (drawn with a dark shadow so it's readable on any background)."""

    x: float
    y: float
    text: str
    colour: str
    size_px: int = 12
    align: TextAlign = TextAlign.CENTRE


Primitive = Line | Rect | FilledRect | Circle | Text


@dataclass(frozen=True, slots=True)
class OverlayFrame:
    """Everything the overlay needs for one repaint: where to sit and what to draw."""

    visible: bool = False
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    primitives: tuple[Primitive, ...] = field(default_factory=tuple)
