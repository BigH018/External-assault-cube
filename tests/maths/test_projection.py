"""Tests for maths/projection.py.

The key test builds the view matrix exactly the way AssaultCube's renderer does
(helpers.gl_matrix.ac_view_projection) and checks that a point straight along the view direction
(from maths/angles.py) lands at the screen centre. That ties our yaw convention to the engine's own transform.
"""

from __future__ import annotations

import pytest

from actrainer.game.structs import Vec3
from actrainer.maths import vectors
from actrainer.maths.angles import Angles, direction_from_angles
from actrainer.maths.projection import fov_circle_radius, world_to_screen
from actrainer.maths.skeleton import facing_vectors
from helpers import gl_matrix as gl

W, H = 1600.0, 900.0
CAM = (120.0, 80.0, 6.0)
CAM_V = Vec3(*CAM)
IDENTITY = gl.to_column_major(gl.identity())


# --- basic layout ---------------------------------------------------------------

def test_identity_matrix_maps_ndc_to_pixels_with_y_flipped() -> None:
    assert world_to_screen(Vec3(0, 0, 0), IDENTITY, W, H) == pytest.approx((W / 2, H / 2))
    assert world_to_screen(Vec3(1, 1, 0), IDENTITY, W, H) == pytest.approx((W, 0))     # NDC top-right
    assert world_to_screen(Vec3(-1, -1, 0), IDENTITY, W, H) == pytest.approx((0, H))   # NDC bottom-left


def test_matrix_is_read_column_major() -> None:
    # Translation lives in m[12], m[13] in column-major. Shift x by +0.5 NDC: centre moves right by W/4.
    m = gl.to_column_major(gl.translate(0.5, 0.0, 0.0))
    assert m[12] == 0.5
    assert world_to_screen(Vec3(0, 0, 0), m, W, H) == pytest.approx((W / 2 + W / 4, H / 2))


def test_rejects_wrong_matrix_size() -> None:
    with pytest.raises(ValueError):
        world_to_screen(Vec3(0, 0, 0), (1.0,) * 12, W, H)


def test_plain_perspective_exact_values() -> None:
    # GL camera at origin looking down -z, fovy 90, aspect 1: point (10, 0, -10) is on the right edge.
    m = gl.to_column_major(gl.perspective(90, 1.0, 0.1, 100))
    assert world_to_screen(Vec3(0, 0, -10), m, 800, 800) == pytest.approx((400, 400))
    assert world_to_screen(Vec3(10, 0, -10), m, 800, 800) == pytest.approx((800, 400))
    assert world_to_screen(Vec3(0, 10, -10), m, 800, 800) == pytest.approx((400, 0))
    assert world_to_screen(Vec3(0, 0, 10), m, 800, 800) is None  # behind the camera


# --- AssaultCube-style camera -------------------------------------------------------

@pytest.mark.parametrize("yaw, pitch", [(0, 0), (90, 0), (180, 0), (270, 0), (33, 15), (300, -40), (359, 70)])
def test_point_along_view_direction_is_screen_centre(yaw: float, pitch: float) -> None:
    m = gl.ac_view_projection(CAM, yaw, pitch, width=W, height=H)
    target = vectors.add(CAM_V, vectors.scale(direction_from_angles(Angles(yaw, pitch)), 30))
    assert world_to_screen(target, m, W, H) == pytest.approx((W / 2, H / 2), abs=1e-3)


@pytest.mark.parametrize("yaw", [0, 45, 135, 250])
def test_point_behind_camera_is_rejected(yaw: float) -> None:
    m = gl.ac_view_projection(CAM, yaw, 0, width=W, height=H)
    behind = vectors.sub(CAM_V, vectors.scale(direction_from_angles(Angles(yaw, 0)), 30))
    assert world_to_screen(behind, m, W, H) is None


@pytest.mark.parametrize("yaw", [0, 90, 200])
def test_up_is_up_and_right_is_right(yaw: float) -> None:
    m = gl.ac_view_projection(CAM, yaw, 0, width=W, height=H)
    forward, right = facing_vectors(yaw)
    ahead = vectors.add(CAM_V, vectors.scale(forward, 30))
    above = world_to_screen(vectors.add(ahead, Vec3(0, 0, 3)), m, W, H)
    to_right = world_to_screen(vectors.add(ahead, vectors.scale(right, 3)), m, W, H)
    assert above is not None and above[1] < H / 2          # higher in world = smaller screen y
    assert to_right is not None and to_right[0] > W / 2    # skeleton's "right" is screen right


def test_further_objects_appear_closer_to_centre() -> None:
    m = gl.ac_view_projection(CAM, 90, 0, width=W, height=H)
    near = world_to_screen(Vec3(CAM[0] + 10, CAM[1], CAM[2] + 2), m, W, H)
    far = world_to_screen(Vec3(CAM[0] + 50, CAM[1], CAM[2] + 2), m, W, H)
    assert near is not None and far is not None
    assert abs(far[1] - H / 2) < abs(near[1] - H / 2)


def test_horizontal_fov_edge_lands_on_screen_edge() -> None:
    # hfov 90: a point 45 degrees right of centre (level) lands on the right edge.
    m = gl.ac_view_projection(CAM, 0, 0, hfov_deg=90, width=W, height=H)
    edge = vectors.add(CAM_V, vectors.scale(direction_from_angles(Angles(45, 0)), 30))
    x, y = world_to_screen(edge, m, W, H)
    assert y == pytest.approx(H / 2, abs=1e-3)
    assert x == pytest.approx(W, abs=1e-3) or x == pytest.approx(0, abs=1e-3)


# --- FOV circle -------------------------------------------------------------------

def test_fov_circle_radius() -> None:
    assert fov_circle_radius(0, 90, W) == pytest.approx(0)
    assert fov_circle_radius(45, 90, W) == pytest.approx(W / 2)   # half the hfov reaches the edge
    assert fov_circle_radius(10, 90, W) < fov_circle_radius(20, 90, W)
    assert fov_circle_radius(90, 90, W) > W                       # "everything", no infinity
