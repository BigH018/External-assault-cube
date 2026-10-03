"""Read the camera: the view matrix and the field of view.

The view matrix is 16 floats stored IN PLACE at module + VIEW_MATRIX (it is NOT a pointer), in
OpenGL column-major order. It's the combined projection x modelview matrix the game renders with,
so maths/projection.world_to_screen can use it directly.
"""

from __future__ import annotations

import math

from actrainer import offsets
from actrainer.maths.projection import MATRIX_SIZE
from actrainer.memory.process import GameProcess


def read_view_matrix(proc: GameProcess) -> tuple[float, ...]:
    """The 16-float view-projection matrix (column-major).

    Raises:
        MemoryAccessError: if the read fails.
    """
    return proc.read_f32_array(proc.module_base + offsets.VIEW_MATRIX, MATRIX_SIZE)


def read_fov(proc: GameProcess) -> float:
    """The game's (horizontal) field of view in degrees.

    Raises:
        MemoryAccessError: if the read fails.
    """
    return proc.read_f32(proc.module_base + offsets.VIEW_FOV)


def horizontal_fov_from_matrix(matrix: tuple[float, ...]) -> float:
    """Horizontal FOV (degrees) implied by the matrix.

    Row 0 of projection x rotation has length 1/tan(hfov/2), because rotation keeps lengths and only the
    projection's x scale remains. Used to confirm that offsets.VIEW_FOV is the HORIZONTAL fov.
    """
    row0_length = math.sqrt(matrix[0] ** 2 + matrix[4] ** 2 + matrix[8] ** 2)  # column-major: row 0 = m[0], m[4], m[8]
    return math.degrees(2 * math.atan(1 / row0_length))


def is_sane_matrix(matrix: tuple[float, ...]) -> bool:
    """True if the matrix is 16 finite numbers and not all zero (e.g. before the first frame renders)."""
    return len(matrix) == MATRIX_SIZE and all(math.isfinite(v) for v in matrix) and any(matrix)
