"""Tests for maths/vectors.py."""

from __future__ import annotations

import pytest

from actrainer.game.structs import Vec3
from actrainer.maths import vectors as v


def test_add_sub_scale() -> None:
    a, b = Vec3(1, 2, 3), Vec3(4, 6, 8)
    assert v.add(a, b) == Vec3(5, 8, 11)
    assert v.sub(b, a) == Vec3(3, 4, 5)
    assert v.scale(a, 2) == Vec3(2, 4, 6)


def test_dot_and_cross() -> None:
    x, y, z = Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)
    assert v.dot(x, y) == 0
    assert v.dot(x, x) == 1
    assert v.cross(x, y) == z


def test_lengths_and_distance() -> None:
    assert v.length(Vec3(3, 4, 0)) == pytest.approx(5)
    assert v.length_2d(Vec3(3, 4, 100)) == pytest.approx(5)
    assert v.distance(Vec3(1, 1, 1), Vec3(1, 1, 4)) == pytest.approx(3)


def test_normalize() -> None:
    n = v.normalize(Vec3(0, 0, 7))
    assert n == Vec3(0, 0, 1)
    assert v.normalize(v.ZERO) == v.ZERO  # no division by zero


def test_lerp() -> None:
    a, b = Vec3(0, 0, 0), Vec3(10, 20, 30)
    assert v.lerp(a, b, 0) == a
    assert v.lerp(a, b, 1) == b
    assert v.lerp(a, b, 0.5) == Vec3(5, 10, 15)
