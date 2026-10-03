"""Aim angles in AssaultCube's convention: normalisation, smoothing and FOV checks.

AssaultCube convention (derived from the game's own `vecfromyawpitch()`):
    forward direction = (sin(yaw) * cos(pitch), -cos(yaw) * cos(pitch), sin(pitch))
    - angles are in DEGREES
    - yaw 0 faces -y, yaw 90 faces +x, yaw is kept in [0, 360)
    - pitch 0 is level, +90 straight up, -90 straight down

Inverting that for a target offset (dx, dy, dz):
    yaw   = atan2(dx, -dy)                  == standard atan2(dy, dx) + 90 degrees
    pitch = atan2(dz, horizontal distance)

That "+90" is the famous AC yaw offset: standard maths measures angles from +x,
AC measures them from -y.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from actrainer.game.structs import Vec3
from actrainer.maths import vectors

YAW_FULL_TURN = 360.0
YAW_HALF_TURN = 180.0
PITCH_MIN = -90.0
PITCH_MAX = 90.0
MIN_SMOOTHING = 1.0


class Angles(NamedTuple):
    """A view direction in AC degrees."""

    yaw: float
    pitch: float


def normalize_yaw(yaw: float) -> float:
    """Wrap any yaw into [0, 360). Python's % already returns a non-negative result for a positive modulus."""
    wrapped = yaw % YAW_FULL_TURN
    # -1e-15 % 360 rounds to exactly 360.0 in floating point. Fold it back to 0.
    return 0.0 if wrapped >= YAW_FULL_TURN else wrapped


def clamp_pitch(pitch: float) -> float:
    """Clamp pitch to [-90, 90] (you can't look past straight up or down)."""
    return max(PITCH_MIN, min(PITCH_MAX, pitch))


def yaw_delta(from_yaw: float, to_yaw: float) -> float:
    """Signed SHORTEST rotation from one yaw to another, in (-180, 180].

    Example: from 350 to 10 is +20 (turn through 0/360), not -340 (the long way round).
    """
    d = (to_yaw - from_yaw) % YAW_FULL_TURN  # now in [0, 360)
    return d - YAW_FULL_TURN if d > YAW_HALF_TURN else d


def calc_aim_angles(origin: Vec3, target: Vec3) -> Angles:
    """Yaw/pitch that point the view from `origin` (the eye) at `target`."""
    d = vectors.sub(target, origin)
    yaw = math.degrees(math.atan2(d.x, -d.y))  # AC: yaw 0 faces -y (see module docstring)
    pitch = math.degrees(math.atan2(d.z, vectors.length_2d(d)))
    return Angles(normalize_yaw(yaw), clamp_pitch(pitch))


def direction_from_angles(angles: Angles) -> Vec3:
    """Unit forward vector for a view direction (the inverse of calc_aim_angles)."""
    yaw, pitch = math.radians(angles.yaw), math.radians(angles.pitch)
    cos_p = math.cos(pitch)
    return Vec3(math.sin(yaw) * cos_p, -math.cos(yaw) * cos_p, math.sin(pitch))


def angular_distance(a: Angles, b: Angles) -> float:
    """True angle in degrees between two view directions (0 = same direction, 180 = opposite).

    Uses the dot product of the two direction vectors, so it stays correct near straight up or down,
    where simple yaw differences become meaningless.
    """
    cos_angle = vectors.dot(direction_from_angles(a), direction_from_angles(b))
    # Rounding can push the dot product a hair past ±1, and acos would raise.
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_angle))))


def is_within_fov(view: Angles, target: Angles, fov_radius_deg: float) -> bool:
    """True if `target` is within `fov_radius_deg` degrees of where we're looking."""
    return angular_distance(view, target) <= fov_radius_deg


def smooth_angles(current: Angles, target: Angles, smoothing: float) -> Angles:
    """Move part of the way from `current` towards `target` (call once per tick).

    Each call covers 1/smoothing of the remaining distance: 1 = instant snap, 5 = a fifth per tick.
    Yaw moves along the SHORTEST direction, so it never spins the long way past 0/360.
    Note: the speed depends on the tick rate (more ticks per second = faster aim).
    """
    factor = 1.0 / max(MIN_SMOOTHING, smoothing)
    yaw = current.yaw + yaw_delta(current.yaw, target.yaw) * factor
    pitch = current.pitch + (target.pitch - current.pitch) * factor
    return Angles(normalize_yaw(yaw), clamp_pitch(pitch))
