"""Minimal OpenGL fixed-function matrix maths for tests (pure Python, no numpy).

Matrices are 4x4 row-major nested lists for multiplication; `to_column_major` flattens them into
the 16-float layout the game stores (and world_to_screen expects).
Each gl* helper returns the matrix that OpenGL would post-multiply onto the current one.
"""

from __future__ import annotations

import math

Matrix = list[list[float]]


def identity() -> Matrix:
    return [[1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]


def multiply(a: Matrix, b: Matrix) -> Matrix:
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def chain(*ms: Matrix) -> Matrix:
    """a * b * c ... (same order as successive glXxx calls)."""
    out = identity()
    for m in ms:
        out = multiply(out, m)
    return out


def to_column_major(m: Matrix) -> tuple[float, ...]:
    return tuple(m[r][c] for c in range(4) for r in range(4))


def translate(x: float, y: float, z: float) -> Matrix:
    m = identity()
    m[0][3], m[1][3], m[2][3] = x, y, z
    return m


def scale(x: float, y: float, z: float) -> Matrix:
    m = identity()
    m[0][0], m[1][1], m[2][2] = x, y, z
    return m


def rotate(angle_deg: float, x: float, y: float, z: float) -> Matrix:
    """glRotatef: rotate angle_deg around axis (x, y, z)."""
    n = math.sqrt(x * x + y * y + z * z)
    x, y, z = x / n, y / n, z / n
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    t = 1 - c
    return [
        [x * x * t + c, x * y * t - z * s, x * z * t + y * s, 0.0],
        [y * x * t + z * s, y * y * t + c, y * z * t - x * s, 0.0],
        [x * z * t - y * s, y * z * t + x * s, z * z * t + c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def perspective(fovy_deg: float, aspect: float, near: float, far: float) -> Matrix:
    """gluPerspective."""
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    return [
        [f / aspect, 0.0, 0.0, 0.0],
        [0.0, f, 0.0, 0.0],
        [0.0, 0.0, (far + near) / (near - far), 2 * far * near / (near - far)],
        [0.0, 0.0, -1.0, 0.0],
    ]


def ac_view_projection(cam: tuple[float, float, float], yaw: float, pitch: float,
                       hfov_deg: float = 90.0, width: float = 1600, height: float = 900) -> tuple[float, ...]:
    """Build the matrix the way AssaultCube's renderer does (transplayer() + gluPerspective).

        glRotatef(pitch, -1, 0, 0); glRotatef(yaw, 0, 1, 0);
        glRotatef(-90, 1, 0, 0); glScalef(1, -1, 1);       // RH GL space -> Z-up "quake style" world
        glTranslatef(-cam.x, -cam.y, -cam.z);

    AC's fov setting is horizontal; fovy is derived from it and the aspect ratio.
    """
    aspect = width / height
    fovy = math.degrees(2 * math.atan(math.tan(math.radians(hfov_deg) / 2) / aspect))
    m = chain(
        perspective(fovy, aspect, 0.15, 1000.0),
        rotate(pitch, -1, 0, 0),
        rotate(yaw, 0, 1, 0),
        rotate(-90, 1, 0, 0),
        scale(1, -1, 1),
        translate(-cam[0], -cam[1], -cam[2]),
    )
    return to_column_major(m)
