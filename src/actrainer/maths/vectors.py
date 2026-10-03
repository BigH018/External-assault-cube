"""Small vector helpers for Vec3. Pure functions, no I/O."""

from __future__ import annotations

import math

from actrainer.game.structs import Vec3

ZERO = Vec3(0.0, 0.0, 0.0)
UP = Vec3(0.0, 0.0, 1.0)  # AssaultCube's z axis points up


def add(a: Vec3, b: Vec3) -> Vec3:
    """a + b."""
    return Vec3(a.x + b.x, a.y + b.y, a.z + b.z)


def sub(a: Vec3, b: Vec3) -> Vec3:
    """a - b: the vector pointing FROM b TO a."""
    return Vec3(a.x - b.x, a.y - b.y, a.z - b.z)


def scale(v: Vec3, k: float) -> Vec3:
    """v * k."""
    return Vec3(v.x * k, v.y * k, v.z * k)


def dot(a: Vec3, b: Vec3) -> float:
    """Dot product. For unit vectors it is the cosine of the angle between them."""
    return a.x * b.x + a.y * b.y + a.z * b.z


def cross(a: Vec3, b: Vec3) -> Vec3:
    """Cross product: a vector perpendicular to both a and b."""
    return Vec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x)


def length(v: Vec3) -> float:
    """Euclidean length of v."""
    return math.sqrt(dot(v, v))


def length_2d(v: Vec3) -> float:
    """Length of v ignoring height (z)."""
    return math.hypot(v.x, v.y)


def distance(a: Vec3, b: Vec3) -> float:
    """Straight-line distance between two points."""
    return length(sub(a, b))


def normalize(v: Vec3) -> Vec3:
    """v scaled to length 1. Returns ZERO for a zero vector instead of dividing by zero."""
    n = length(v)
    return ZERO if n == 0.0 else scale(v, 1.0 / n)


def lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    """Linear interpolation: t=0 gives a, t=1 gives b."""
    return Vec3(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t)
