"""Tests for features/aimbot.py (pure target selection + aiming)."""

from __future__ import annotations

import pytest

from actrainer.features.aimbot import BODY_HEIGHT_FRACTION, aim_point, compute_aim, find_candidates, select_target
from actrainer.game.structs import PlayerSnapshot, Vec3
from actrainer.maths.angles import Angles, angular_distance, calc_aim_angles
from actrainer.settings.models import AimbotSettings, AimTarget, TargetPriority

EYE_HEIGHT = 4.5


def player(name: str, x: float, y: float, z: float = 0.0, health: int = 100, team: int = 1,
           dead: bool = False, yaw: float = 90.0, pitch: float = 0.0, address: int = 0) -> PlayerSnapshot:
    """A player standing with feet at (x, y, z)."""
    return PlayerSnapshot(address=address or hash(name) & 0xFFFFFF, name=name, head=Vec3(x, y, z + EYE_HEIGHT),
                          feet=Vec3(x, y, z), yaw=yaw, pitch=pitch, health=health, armor=0, team=team, dead=dead)


# Local player at (100, 100) looking along +x (AC yaw 90), level.
ME = player("me", 100, 100, team=0, yaw=90.0, pitch=0.0)


def settings(**overrides: object) -> AimbotSettings:
    s = AimbotSettings(enabled=True, fov_deg=30.0, max_distance=500.0, smoothing=1.0)
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


# --- aim point --------------------------------------------------------------------

def test_aim_point_head_and_body() -> None:
    bot = player("b", 0, 0)
    assert aim_point(bot, AimTarget.HEAD) == bot.head
    body = aim_point(bot, AimTarget.BODY)
    assert body.z == pytest.approx(EYE_HEIGHT * BODY_HEIGHT_FRACTION)
    assert (body.x, body.y) == (0, 0)


# --- filters ---------------------------------------------------------------------------

def test_fov_filter() -> None:
    ahead = player("ahead", 150, 100)       # straight ahead: 0 deg off
    side = player("side", 100, 150)         # 90 deg to the side
    names = [c.player.name for c in find_candidates(ME, [ahead, side], settings(fov_deg=30))]
    assert names == ["ahead"]
    names = [c.player.name for c in find_candidates(ME, [ahead, side], settings(fov_deg=180))]
    assert sorted(names) == ["ahead", "side"]


def test_dead_and_zero_health_always_ignored() -> None:
    bots = [player("dead", 150, 100, dead=True), player("zero", 150, 101, health=0), player("ok", 150, 99)]
    assert [c.player.name for c in find_candidates(ME, bots, settings())] == ["ok"]


def test_team_check() -> None:
    mate = player("mate", 150, 100, team=0)   # same team as ME
    enemy = player("enemy", 150, 101, team=1)
    assert len(find_candidates(ME, [mate, enemy], settings(team_check=False))) == 2
    assert [c.player.name for c in find_candidates(ME, [mate, enemy], settings(team_check=True))] == ["enemy"]


def test_max_distance() -> None:
    near = player("near", 150, 100)
    far = player("far", 900, 100)
    assert [c.player.name for c in find_candidates(ME, [near, far], settings(max_distance=200))] == ["near"]


# --- priority ---------------------------------------------------------------------------

BOTS = [
    player("centre_far", 400, 100, health=90),     # 0 deg off, 300 away
    player("off_near", 130, 110, health=70),       # ~18 deg off, ~32 away
    player("off_weak", 200, 125, health=10),       # ~14 deg off, ~103 away
]


@pytest.mark.parametrize("priority, expected", [
    (TargetPriority.CROSSHAIR, "centre_far"),
    (TargetPriority.DISTANCE, "off_near"),
    (TargetPriority.HEALTH, "off_weak"),
])
def test_priority(priority: TargetPriority, expected: str) -> None:
    chosen = select_target(ME, BOTS, settings(priority=priority))
    assert chosen is not None and chosen.player.name == expected


def test_priority_tie_broken_by_crosshair() -> None:
    a = player("a", 200, 120, health=50)   # further off-centre
    b = player("b", 200, 105, health=50)   # closer to crosshair
    chosen = select_target(ME, [a, b], settings(priority=TargetPriority.HEALTH))
    assert chosen is not None and chosen.player.name == "b"


def test_no_candidates_gives_none() -> None:
    assert select_target(ME, [], settings()) is None
    assert compute_aim(ME, [player("behind", 50, 100)], settings()) is None  # 180 deg off


# --- aiming -------------------------------------------------------------------------------

def test_snap_aims_exactly_at_head() -> None:
    bot = player("b", 150, 120, z=2.0)
    result = compute_aim(ME, [bot], settings(smoothing=1))
    assert result is not None
    angles, target = result
    assert target.player is bot
    assert angles == pytest.approx(calc_aim_angles(ME.head, bot.head))


def test_smoothing_moves_part_of_the_way() -> None:
    bot = player("b", 150, 120)
    snap = calc_aim_angles(ME.head, bot.head)
    angles, _ = compute_aim(ME, [bot], settings(smoothing=4))  # type: ignore[misc]
    full = angular_distance(Angles(ME.yaw, ME.pitch), snap)
    moved = angular_distance(Angles(ME.yaw, ME.pitch), angles)
    assert moved == pytest.approx(full / 4, rel=0.05)


def test_body_target_aims_lower_than_head() -> None:
    bot = player("b", 150, 100)
    head, _ = compute_aim(ME, [bot], settings(target=AimTarget.HEAD))  # type: ignore[misc]
    body, _ = compute_aim(ME, [bot], settings(target=AimTarget.BODY))  # type: ignore[misc]
    assert body.pitch < head.pitch


def test_does_not_aim_while_dead() -> None:
    dead_me = player("me", 100, 100, team=0, dead=True)
    assert compute_aim(dead_me, [player("b", 150, 100)], settings()) is None


def test_crosses_0_360_the_short_way() -> None:
    # Looking at yaw 355 (just west of north); target just east of north (yaw ~5).
    me = player("me", 100, 100, team=0, yaw=355.0)
    bot = player("b", 102, 50)  # nearly straight -y = north = yaw ~2.3
    angles, _ = compute_aim(me, [bot], settings(smoothing=2))  # type: ignore[misc]
    assert angles.yaw > 355 or angles.yaw < 5  # halfway through 0, never via 180
