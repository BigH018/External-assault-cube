"""Tests for maths/angles.py (AssaultCube yaw/pitch convention)."""

from __future__ import annotations

import pytest

from actrainer.game.structs import Vec3
from actrainer.maths import vectors
from actrainer.maths.angles import (
    Angles,
    angular_distance,
    calc_aim_angles,
    clamp_pitch,
    direction_from_angles,
    is_within_fov,
    normalize_yaw,
    smooth_angles,
    yaw_delta,
)

EYE = Vec3(100.0, 100.0, 5.0)


# --- calc_aim_angles: AC yaw 0 faces -y, 90 faces +x ----------------------------

@pytest.mark.parametrize("offset, yaw", [
    (Vec3(0, -10, 0), 0.0),     # straight "north" (-y)
    (Vec3(10, 0, 0), 90.0),     # +x
    (Vec3(0, 10, 0), 180.0),    # +y
    (Vec3(-10, 0, 0), 270.0),   # -x
    (Vec3(10, -10, 0), 45.0),
])
def test_calc_aim_yaw_cardinal_directions(offset: Vec3, yaw: float) -> None:
    angles = calc_aim_angles(EYE, vectors.add(EYE, offset))
    assert angles.yaw == pytest.approx(yaw)
    assert angles.pitch == pytest.approx(0.0)


def test_calc_aim_yaw_is_standard_atan2_plus_90() -> None:
    # The documented gotcha: AC yaw = atan2(dy, dx) in degrees + 90.
    import math
    d = Vec3(3.0, 7.0, 0.0)
    expected = normalize_yaw(math.degrees(math.atan2(d.y, d.x)) + 90.0)
    assert calc_aim_angles(EYE, vectors.add(EYE, d)).yaw == pytest.approx(expected)


@pytest.mark.parametrize("offset, pitch", [
    (Vec3(10, 0, 10), 45.0),     # up at 45 degrees
    (Vec3(10, 0, -10), -45.0),   # down at 45 degrees
    (Vec3(0, 0, 10), 90.0),      # straight up
    (Vec3(0, 0, -10), -90.0),    # straight down
])
def test_calc_aim_pitch(offset: Vec3, pitch: float) -> None:
    assert calc_aim_angles(EYE, vectors.add(EYE, offset)).pitch == pytest.approx(pitch)


@pytest.mark.parametrize("yaw, pitch", [(0, 0), (37, 12), (90, -30), (181, 60), (359.5, -89)])
def test_direction_and_aim_angles_round_trip(yaw: float, pitch: float) -> None:
    target = vectors.add(EYE, vectors.scale(direction_from_angles(Angles(yaw, pitch)), 50))
    got = calc_aim_angles(EYE, target)
    assert got.yaw == pytest.approx(yaw, abs=1e-6)
    assert got.pitch == pytest.approx(pitch, abs=1e-6)


# --- normalisation ------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [(0, 0), (359.9, 359.9), (360, 0), (725, 5), (-10, 350),
                                           (-370, 350), (-1e-15, 0)])
def test_normalize_yaw(raw: float, expected: float) -> None:
    got = normalize_yaw(raw)
    assert got == pytest.approx(expected)
    assert 0 <= got < 360


@pytest.mark.parametrize("raw, expected", [(0, 0), (45, 45), (120, 90), (-100, -90)])
def test_clamp_pitch(raw: float, expected: float) -> None:
    assert clamp_pitch(raw) == expected


@pytest.mark.parametrize("a, b, delta", [(350, 10, 20), (10, 350, -20), (0, 90, 90), (90, 0, -90),
                                         (0, 180, 180), (359, 1, 2), (1, 359, -2), (45, 45, 0)])
def test_yaw_delta_is_shortest(a: float, b: float, delta: float) -> None:
    assert yaw_delta(a, b) == pytest.approx(delta)


# --- smoothing ------------------------------------------------------------------

def test_smoothing_1_snaps_instantly() -> None:
    assert smooth_angles(Angles(10, 0), Angles(200, 30), 1) == pytest.approx(Angles(200, 30))


def test_smoothing_below_1_is_treated_as_snap() -> None:
    assert smooth_angles(Angles(10, 0), Angles(200, 30), 0.2) == pytest.approx(Angles(200, 30))


def test_smoothing_moves_fraction_of_the_way() -> None:
    got = smooth_angles(Angles(0, 0), Angles(40, 20), 4)
    assert got == pytest.approx(Angles(10, 5))


def test_smoothing_crosses_0_360_the_short_way() -> None:
    got = smooth_angles(Angles(350, 0), Angles(10, 0), 2)
    assert got.yaw == pytest.approx(0.0, abs=1e-9)  # halfway through 0, not 180


def test_smoothing_never_spins_the_long_way() -> None:
    current = Angles(350.0, 0.0)
    for _ in range(50):
        current = smooth_angles(current, Angles(10.0, 0.0), 3)
        assert current.yaw >= 350.0 or current.yaw <= 10.0
    assert current.yaw == pytest.approx(10.0, abs=1e-3)


def test_smoothing_clamps_pitch() -> None:
    assert smooth_angles(Angles(0, 80), Angles(0, 200), 1).pitch == 90


# --- FOV ------------------------------------------------------------------------

def test_angular_distance_basics() -> None:
    assert angular_distance(Angles(30, 10), Angles(30, 10)) == pytest.approx(0, abs=1e-6)
    assert angular_distance(Angles(0, 0), Angles(90, 0)) == pytest.approx(90)
    assert angular_distance(Angles(0, 0), Angles(180, 0)) == pytest.approx(180)
    assert angular_distance(Angles(355, 0), Angles(5, 0)) == pytest.approx(10)


def test_angular_distance_near_the_pole_is_small() -> None:
    # Looking almost straight up, a 180 degree yaw difference is only a 2 degree angle.
    assert angular_distance(Angles(0, 89), Angles(180, 89)) == pytest.approx(2, abs=1e-6)


def test_is_within_fov() -> None:
    assert is_within_fov(Angles(0, 0), Angles(8, 0), 10)
    assert not is_within_fov(Angles(0, 0), Angles(12, 0), 10)
    assert is_within_fov(Angles(358, 0), Angles(3, 0), 10)  # across 0/360
