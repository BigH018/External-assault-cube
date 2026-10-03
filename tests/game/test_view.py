"""Tests for game/view.py."""

from __future__ import annotations

import pytest

from actrainer.game.view import horizontal_fov_from_matrix, is_sane_matrix, read_fov, read_view_matrix
from helpers import gl_matrix as gl
from helpers.fake_game import IDENTITY_MATRIX, make_fake_game


def test_reads_matrix_in_place_and_fov() -> None:
    proc, _, _ = make_fake_game(fov=75.0)
    assert read_view_matrix(proc) == IDENTITY_MATRIX
    assert read_fov(proc) == pytest.approx(75.0)


@pytest.mark.parametrize("hfov", [70.0, 90.0, 110.0])
@pytest.mark.parametrize("yaw, pitch", [(0, 0), (123, 30), (300, -60)])
def test_horizontal_fov_recovered_from_ac_style_matrix(hfov: float, yaw: float, pitch: float) -> None:
    m = gl.ac_view_projection((50.0, 60.0, 5.0), yaw, pitch, hfov_deg=hfov, width=1920, height=1080)
    assert horizontal_fov_from_matrix(m) == pytest.approx(hfov, abs=1e-6)


def test_live_matrix_from_session_says_fov_90() -> None:
    # Row 0 of the matrix read from the real game on 2026-10-03 (fov setting 90, 1920x1080).
    live_row0 = (0.6031, 0.7977, 0.0)
    m = (live_row0[0], 0, 0, 0, live_row0[1], 0, 0, 0, live_row0[2], 0, 0, 0, 0, 0, 0, 0)
    assert horizontal_fov_from_matrix(m) == pytest.approx(90.0, abs=0.1)


def test_is_sane_matrix() -> None:
    assert is_sane_matrix(IDENTITY_MATRIX)
    assert not is_sane_matrix((0.0,) * 16)                    # before the first frame
    assert not is_sane_matrix((float("nan"),) + (1.0,) * 15)
    assert not is_sane_matrix((1.0,) * 12)
