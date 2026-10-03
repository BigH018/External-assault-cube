"""Tests for maths/skeleton.py."""

from __future__ import annotations

import pytest

from actrainer.game.structs import Vec3
from actrainer.maths import vectors
from actrainer.maths.skeleton import BONES, JOINTS, build_skeleton, facing_vectors

FEET = Vec3(50.0, 60.0, 0.0)
HEAD = Vec3(50.0, 60.0, 4.5)


def test_head_and_feet_line_up_with_inputs() -> None:
    s = build_skeleton(HEAD, FEET, 0)
    assert s.joints["head"] == HEAD
    assert s.joints["foot_r"].z == pytest.approx(FEET.z)
    assert s.joints["foot_l"].z == pytest.approx(FEET.z)


def test_every_joint_is_between_feet_and_head_height() -> None:
    s = build_skeleton(HEAD, FEET, 123)
    for name, j in s.joints.items():
        assert FEET.z - 1e-9 <= j.z <= HEAD.z + 1e-9, name


def test_left_and_right_are_mirrored() -> None:
    s = build_skeleton(HEAD, FEET, 77)
    neck = s.joints["neck"]
    assert vectors.distance(neck, s.joints["shoulder_r"]) == pytest.approx(vectors.distance(neck, s.joints["shoulder_l"]))
    mid = vectors.lerp(s.joints["shoulder_r"], s.joints["shoulder_l"], 0.5)
    assert vectors.distance(mid, neck) < 1e-3 + abs(s.joints["neck"].z - mid.z)


@pytest.mark.parametrize("yaw", [0, 90, 180, 270, 33])
def test_shoulders_are_perpendicular_to_facing_and_hands_in_front(yaw: float) -> None:
    s = build_skeleton(HEAD, FEET, yaw)
    forward, _ = facing_vectors(yaw)
    across = vectors.sub(s.joints["shoulder_r"], s.joints["shoulder_l"])
    assert vectors.dot(across, forward) == pytest.approx(0, abs=1e-9)
    hand_offset = vectors.sub(s.joints["hand_r"], s.joints["pelvis"])
    assert vectors.dot(hand_offset, forward) > 0


def test_facing_vectors_follow_ac_yaw_convention() -> None:
    forward, right = facing_vectors(90)  # yaw 90 faces +x
    assert (forward.x, forward.y) == pytest.approx((1, 0), abs=1e-9)
    assert vectors.dot(forward, right) == pytest.approx(0, abs=1e-9)
    assert vectors.length(right) == pytest.approx(1)


def test_crouching_scales_the_figure() -> None:
    standing = build_skeleton(HEAD, FEET, 0)
    crouched = build_skeleton(Vec3(HEAD.x, HEAD.y, FEET.z + 2.25), FEET, 0)  # half height
    w_stand = vectors.distance(standing.joints["shoulder_r"], standing.joints["shoulder_l"])
    w_crouch = vectors.distance(crouched.joints["shoulder_r"], crouched.joints["shoulder_l"])
    assert w_crouch == pytest.approx(w_stand / 2)


def test_bones_reference_real_joints() -> None:
    s = build_skeleton(HEAD, FEET, 0)
    assert all(a in JOINTS and b in JOINTS for a, b in BONES)
    assert len(s.bone_segments()) == len(BONES)
