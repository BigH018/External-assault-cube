"""World-to-screen projection with AssaultCube's OpenGL view matrix.

The game stores a combined (projection * modelview) 4x4 matrix as 16 floats in COLUMN-MAJOR order
(OpenGL style). Element (row r, column c) is at index c*4 + r, so:

    | m[0]  m[4]  m[8]   m[12] |   | x |
    | m[1]  m[5]  m[9]   m[13] | * | y |  =  clip-space (cx, cy, cz, cw)
    | m[2]  m[6]  m[10]  m[14] |   | z |
    | m[3]  m[7]  m[11]  m[15] |   | 1 |

Then:
1. Perspective divide: NDC = (cx/cw, cy/cw), each in [-1, 1] when on screen.
   cw is (roughly) the distance in front of the camera. cw <= 0 means BEHIND the camera, so we
   reject tiny/negative cw instead of dividing by it (that would mirror the point onto the screen).
2. Viewport: NDC x -1..1 -> 0..width. NDC y is UP but screen y goes DOWN, so y is flipped.
"""

from __future__ import annotations

import math

from actrainer.game.structs import Vec3

MATRIX_SIZE = 16
MIN_CLIP_W = 0.001  # anything closer than this (or behind) is not drawable
MAX_FINITE_FOV_DEG = 90.0  # tan() of this is infinite
HUGE_RADIUS_FACTOR = 10.0


def world_to_screen(pos: Vec3, matrix: tuple[float, ...] | list[float],
                    width: float, height: float) -> tuple[float, float] | None:
    """Project a world position to screen pixels, or None if it's behind the camera.

    Args:
        pos: world position.
        matrix: 16 floats, OpenGL column-major (as read from offsets.VIEW_MATRIX).
        width, height: size of the game's client area in pixels.

    Returns:
        (x, y) in pixels from the top-left of the client area. Points beside or past the screen
        edges still return coordinates (outside 0..width/0..height) so lines can be clipped by the painter.

    Raises:
        ValueError: if the matrix doesn't have 16 elements.
    """
    if len(matrix) != MATRIX_SIZE:
        raise ValueError(f"view matrix must have {MATRIX_SIZE} floats, got {len(matrix)}")
    m = matrix
    clip_x = m[0] * pos.x + m[4] * pos.y + m[8] * pos.z + m[12]
    clip_y = m[1] * pos.x + m[5] * pos.y + m[9] * pos.z + m[13]
    clip_w = m[3] * pos.x + m[7] * pos.y + m[11] * pos.z + m[15]
    if clip_w < MIN_CLIP_W:
        return None
    ndc_x = clip_x / clip_w
    ndc_y = clip_y / clip_w
    screen_x = (ndc_x + 1.0) * 0.5 * width
    screen_y = (1.0 - ndc_y) * 0.5 * height  # flip: NDC +y is up, screen +y is down
    return screen_x, screen_y


def fov_circle_radius(aim_fov_deg: float, game_fov_deg: float, screen_width: float) -> float:
    """Pixel radius of a circle covering `aim_fov_deg` degrees around the crosshair.

    In a perspective projection a ray at angle a from the centre lands at
    (tan(a) / tan(hfov / 2)) * (width / 2) pixels from the centre. `game_fov_deg` is the game's
    HORIZONTAL FOV (offsets.VIEW_FOV), to be confirmed in Phase 9.
    If aim_fov reaches 90° or more (tan blows up there), returns a radius far larger than the screen.
    """
    half_width = screen_width / 2.0
    if aim_fov_deg >= MAX_FINITE_FOV_DEG:
        return half_width * HUGE_RADIUS_FACTOR  # effectively "everything"; avoids tan(90°) = infinity
    half_hfov = math.radians(game_fov_deg) / 2.0
    return math.tan(math.radians(aim_fov_deg)) / math.tan(half_hfov) * half_width
