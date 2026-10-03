"""Tests for features/esp.py using an AssaultCube-style camera matrix (no Qt, no game)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from actrainer.features.esp import (
    BOX_ASPECT,
    HEALTH_BAR_WIDTH,
    build_esp,
    health_colour,
    screen_box,
)
from actrainer.features.primitives import Circle, FilledRect, Line, Rect, Text
from actrainer.game.structs import GameState, PlayerSnapshot, Vec3
from actrainer.maths.projection import fov_circle_radius
from actrainer.maths.skeleton import BONES
from actrainer.settings.models import AimbotSettings, EspSettings, SnaplineOrigin
from helpers import gl_matrix as gl

W, H = 1600, 900
EYE = 4.5


def player(name: str, x: float, y: float, team: int = 1, health: int = 100, address: int = 0) -> PlayerSnapshot:
    return PlayerSnapshot(address=address or (hash(name) & 0xFFFFFF), name=name, head=Vec3(x, y, EYE),
                          feet=Vec3(x, y, 0.0), yaw=270.0, pitch=0.0, health=health, armor=0, team=team, dead=False)


ME = player("me", 0, 0, team=0)
# Camera at our eye looking along +x (AC yaw 90), level, hfov 90.
MATRIX = gl.ac_view_projection((0.0, 0.0, EYE), 90.0, 0.0, hfov_deg=90.0, width=W, height=H)


def state(*bots: PlayerSnapshot, fov: float = 90.0) -> GameState:
    return GameState(local=ME, entities=tuple(bots), view_matrix=MATRIX, fov=fov)


def esp(**overrides: object) -> EspSettings:
    base = EspSettings(enabled=True, box_2d=False, corner_box=False, head_circle=False, skeleton=False,
                       show_name=False, show_health_bar=False, show_health_number=False, show_distance=False,
                       show_snaplines=False)
    return replace(base, **overrides)


NO_AIM = AimbotSettings(enabled=False)


def of_type(prims: list, cls: type) -> list:
    return [p for p in prims if isinstance(p, cls)]


# --- box geometry ---------------------------------------------------------------------

def test_box_for_bot_straight_ahead_is_centred_and_upright() -> None:
    box = screen_box(player("b", 50, 0), MATRIX, W, H)
    assert box is not None
    assert box.centre_x == pytest.approx(W / 2, abs=0.5)
    assert box.y < H / 2 < box.bottom          # head above centre, feet below (we're at eye height)
    assert box.w == pytest.approx(box.h * BOX_ASPECT)


def test_nearer_bot_has_bigger_box() -> None:
    near = screen_box(player("n", 20, 0), MATRIX, W, H)
    far = screen_box(player("f", 80, 0), MATRIX, W, H)
    assert near is not None and far is not None and near.h > far.h


def test_bot_behind_camera_is_skipped() -> None:
    assert screen_box(player("b", -50, 0), MATRIX, W, H) is None
    assert build_esp(state(player("b", -50, 0)), esp(box_2d=True), NO_AIM, W, H) == []


def test_bot_to_the_right_is_right_of_centre() -> None:
    # Facing +x, the player's right is up x forward = +y (turning right increases yaw: 90 (+x) -> 180 (+y)).
    box = screen_box(player("b", 50, 15), MATRIX, W, H)
    assert box is not None and box.centre_x > W / 2


# --- styles ---------------------------------------------------------------------------

def test_disabled_draws_nothing() -> None:
    assert build_esp(state(player("b", 50, 0)), esp(enabled=False, box_2d=True), NO_AIM, W, H) == []


def test_each_style() -> None:
    bot = player("b", 50, 0)
    assert len(of_type(build_esp(state(bot), esp(box_2d=True), NO_AIM, W, H), Rect)) == 1
    assert len(of_type(build_esp(state(bot), esp(corner_box=True), NO_AIM, W, H), Line)) == 8
    assert len(of_type(build_esp(state(bot), esp(head_circle=True), NO_AIM, W, H), Circle)) == 1
    assert len(of_type(build_esp(state(bot), esp(skeleton=True), NO_AIM, W, H), Line)) == len(BONES)


def test_styles_combine() -> None:
    prims = build_esp(state(player("b", 50, 0)), esp(box_2d=True, head_circle=True), NO_AIM, W, H)
    assert len(of_type(prims, Rect)) == 1 and len(of_type(prims, Circle)) == 1


def test_thickness_applies() -> None:
    (rect,) = build_esp(state(player("b", 50, 0)), esp(box_2d=True, thickness=4), NO_AIM, W, H)
    assert rect.thickness == 4


def test_aim_target_is_thicker() -> None:
    bot = player("b", 50, 0, address=0x1234)
    (rect,) = build_esp(state(bot), esp(box_2d=True, thickness=1), NO_AIM, W, H, aim_target_address=0x1234)
    assert rect.thickness > 1


# --- extras ---------------------------------------------------------------------------

def test_name_above_and_info_below() -> None:
    prims = build_esp(state(player("Alpha", 50, 0, health=42)),
                      esp(box_2d=True, show_name=True, show_health_number=True, show_distance=True), NO_AIM, W, H)
    (rect,) = of_type(prims, Rect)
    name, info = of_type(prims, Text)
    assert name.text == "Alpha" and name.y < rect.y
    assert info.text == "42 hp · 50 u" and info.y > rect.y + rect.h


def test_health_bar_fill_proportional() -> None:
    prims = build_esp(state(player("b", 50, 0, health=25)), esp(box_2d=True, show_health_bar=True), NO_AIM, W, H)
    (rect,) = of_type(prims, Rect)
    background, fill = of_type(prims, FilledRect)
    assert background.h == pytest.approx(rect.h)
    assert fill.h == pytest.approx(rect.h * 0.25)
    assert fill.w == HEALTH_BAR_WIDTH and fill.x < rect.x   # left of the box
    assert fill.y + fill.h == pytest.approx(rect.y + rect.h)  # anchored at the bottom


@pytest.mark.parametrize("origin, start_y", [(SnaplineOrigin.BOTTOM, H), (SnaplineOrigin.CENTRE, H / 2)])
def test_snaplines(origin: SnaplineOrigin, start_y: float) -> None:
    (line,) = build_esp(state(player("b", 50, 0)), esp(show_snaplines=True, snapline_origin=origin), NO_AIM, W, H)
    assert (line.x1, line.y1) == (W / 2, start_y)


def test_health_colour_gradient() -> None:
    assert health_colour(100) == "#34C759FF"
    assert health_colour(0) == "#FF3B30FF"
    assert health_colour(250) == health_colour(100)  # clamped


# --- teams ------------------------------------------------------------------------------

def test_ffa_everyone_is_an_enemy() -> None:
    mate = player("m", 50, 0, team=0)  # same team value as ME
    (rect,) = build_esp(state(mate), esp(box_2d=True, team_mode=False, enemies_only=True), NO_AIM, W, H)
    assert rect.colour == EspSettings().enemy_colour


def test_team_mode_colours_and_enemies_only() -> None:
    mate, enemy = player("m", 50, 2, team=0), player("e", 50, -2, team=1)
    prims = build_esp(state(mate, enemy), esp(box_2d=True, team_mode=True), NO_AIM, W, H)
    assert sorted(r.colour for r in of_type(prims, Rect)) == sorted([EspSettings().team_colour, EspSettings().enemy_colour])
    prims = build_esp(state(mate, enemy), esp(box_2d=True, team_mode=True, enemies_only=True), NO_AIM, W, H)
    assert [r.colour for r in of_type(prims, Rect)] == [EspSettings().enemy_colour]


def test_far_players_drawn_first() -> None:
    near, far = player("near", 20, 0), player("far", 80, 0)
    prims = build_esp(state(near, far), esp(box_2d=True), NO_AIM, W, H)
    heights = [r.h for r in of_type(prims, Rect)]
    assert heights == sorted(heights)  # small (far) first, big (near) last = on top


# --- FOV circle ---------------------------------------------------------------------------

def test_fov_circle_only_when_aimbot_enabled_and_drawing() -> None:
    aim = AimbotSettings(enabled=True, draw_fov=True, fov_deg=20.0, fov_thickness=2)
    (circle,) = build_esp(state(), esp(enabled=False), aim, W, H)
    assert (circle.cx, circle.cy) == (W / 2, H / 2)
    assert circle.radius == pytest.approx(fov_circle_radius(20.0, 90.0, W))
    assert circle.thickness == 2
    assert build_esp(state(), esp(enabled=False), replace(aim, draw_fov=False), W, H) == []
    assert build_esp(state(), esp(enabled=False), replace(aim, enabled=False), W, H) == []


def test_fov_circle_edge_matches_projection() -> None:
    # A bot exactly fov_deg off-centre (level) should sit on the circle's edge.
    import math
    aim = AimbotSettings(enabled=True, draw_fov=True, fov_deg=20.0)
    (circle,) = build_esp(state(), esp(enabled=False), aim, W, H)
    angle = math.radians(20.0)
    edge = screen_box(player("e", 50 * math.cos(angle), 50 * math.sin(angle)), MATRIX, W, H)  # 20 deg to the right
    assert edge is not None
    assert edge.centre_x - W / 2 == pytest.approx(circle.radius, rel=0.01)
