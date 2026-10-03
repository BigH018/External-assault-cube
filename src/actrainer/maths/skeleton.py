"""Approximate stick-figure skeleton from head position, feet position and yaw.

The player struct has no bone data, so we build a plausible humanoid from proportions:
- Height h = head.z - feet.z. It shrinks when crouching, so the whole figure scales with it.
- Each joint sits at a fraction of h above the feet, offset sideways (along the body's "right"
  axis) and forwards (along the facing direction).
- The body's centre line is interpolated between feet and head, so a player whose head isn't directly
  above their feet still gets a sensible figure.

"Right" is the player's right as seen on screen. AssaultCube's world is LEFT-handed ("Z-up quake
style" in the renderer), so right = up x forward, not forward x up. This is verified by
tests/maths/test_projection.py::test_up_is_up_and_right_is_right.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

from actrainer.game.structs import Vec3
from actrainer.maths import vectors


class JointSpec(NamedTuple):
    """Where a joint sits, as fractions of player height."""

    up: float        # height above the feet
    side: float      # sideways offset (+ = right, - = left)
    forward: float   # offset in the facing direction


# Proportions tuned for AssaultCube's model. Head = the eye position the game stores (4.5 units above the feet when standing).
JOINTS: dict[str, JointSpec] = {
    "head": JointSpec(1.00, 0.00, 0.00),
    "neck": JointSpec(0.86, 0.00, 0.00),
    "shoulder_r": JointSpec(0.82, 0.17, 0.00),
    "shoulder_l": JointSpec(0.82, -0.17, 0.00),
    "elbow_r": JointSpec(0.62, 0.21, 0.04),
    "elbow_l": JointSpec(0.62, -0.21, 0.04),
    "hand_r": JointSpec(0.46, 0.17, 0.12),
    "hand_l": JointSpec(0.46, -0.17, 0.12),
    "pelvis": JointSpec(0.50, 0.00, 0.00),
    "hip_r": JointSpec(0.50, 0.09, 0.00),
    "hip_l": JointSpec(0.50, -0.09, 0.00),
    "knee_r": JointSpec(0.26, 0.10, 0.03),
    "knee_l": JointSpec(0.26, -0.10, 0.03),
    "foot_r": JointSpec(0.00, 0.10, 0.00),
    "foot_l": JointSpec(0.00, -0.10, 0.00),
}

# Pairs of joints joined by a line when drawing.
BONES: tuple[tuple[str, str], ...] = (
    ("head", "neck"),
    ("neck", "pelvis"),
    ("neck", "shoulder_r"), ("shoulder_r", "elbow_r"), ("elbow_r", "hand_r"),
    ("neck", "shoulder_l"), ("shoulder_l", "elbow_l"), ("elbow_l", "hand_l"),
    ("pelvis", "hip_r"), ("hip_r", "knee_r"), ("knee_r", "foot_r"),
    ("pelvis", "hip_l"), ("hip_l", "knee_l"), ("knee_l", "foot_l"),
)


@dataclass(frozen=True, slots=True)
class Skeleton:
    """World-space joint positions for one player."""

    joints: dict[str, Vec3]

    def bone_segments(self) -> list[tuple[Vec3, Vec3]]:
        """Every bone as a (start, end) pair of world positions."""
        return [(self.joints[a], self.joints[b]) for a, b in BONES]


def facing_vectors(yaw_deg: float) -> tuple[Vec3, Vec3]:
    """Horizontal (forward, right) unit vectors for an AC yaw.

    forward follows AC's convention (yaw 0 faces -y, see maths/angles.py). right is forward rotated
    90 degrees in the horizontal plane. In AC's left-handed world that's up x forward
    (forward x up would point LEFT on screen).
    """
    yaw = math.radians(yaw_deg)
    forward = Vec3(math.sin(yaw), -math.cos(yaw), 0.0)
    right = vectors.cross(vectors.UP, forward)
    return forward, right


def build_skeleton(head: Vec3, feet: Vec3, yaw_deg: float) -> Skeleton:
    """Build an approximate skeleton for a player.

    Args:
        head: the player's head (eye) position.
        feet: the player's feet position.
        yaw_deg: facing direction in AC degrees.
    """
    height = head.z - feet.z
    forward, right = facing_vectors(yaw_deg)
    joints: dict[str, Vec3] = {}
    for name, spec in JOINTS.items():
        # Point on the centre line at this height (handles head not exactly above feet).
        centre = vectors.lerp(feet, head, spec.up)
        offset = vectors.add(vectors.scale(right, spec.side * height),
                             vectors.scale(forward, spec.forward * height))
        joints[name] = vectors.add(centre, offset)
    return Skeleton(joints)
