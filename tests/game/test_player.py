"""Tests for game/player.py: struct parsing and validity checks (no game needed)."""

from __future__ import annotations

import struct

import pytest

from actrainer import offsets
from actrainer.game.player import (
    is_sane_position,
    is_valid_bot,
    is_valid_local_player,
    is_valid_pointer,
    parse_player,
)
from actrainer.game.structs import Vec3

ADDRESS = 0x00ABCDEF


def make_buffer(**overrides: object) -> bytes:
    """Build a fake player struct with sensible values, applying any overrides."""
    values: dict[str, object] = {
        "head": (10.0, 20.0, 5.5), "feet": (10.0, 20.0, 1.0), "yaw": 90.0, "pitch": -10.0,
        "health": 100, "armor": 50, "team": 1, "dead": 0, "name": b"Harry", "grenades": 3,
        "akimbo": 0,
    }
    values.update(overrides)
    buf = bytearray(offsets.PLAYER_READ_SIZE)
    struct.pack_into("<3f", buf, offsets.HEAD_POS, *values["head"])
    struct.pack_into("<3f", buf, offsets.FEET_POS, *values["feet"])
    struct.pack_into("<f", buf, offsets.VIEW_YAW, values["yaw"])
    struct.pack_into("<f", buf, offsets.VIEW_PITCH, values["pitch"])
    struct.pack_into("<i", buf, offsets.HEALTH, values["health"])
    struct.pack_into("<i", buf, offsets.ARMOR, values["armor"])
    struct.pack_into("<i", buf, offsets.TEAM, values["team"])
    struct.pack_into("<i", buf, offsets.DEAD, values["dead"])
    struct.pack_into("<i", buf, offsets.GRENADES, values["grenades"])
    struct.pack_into("<i", buf, offsets.AKIMBO_AMMO, values["akimbo"])
    for i, off in enumerate(offsets.MAG_AMMO.values()):
        struct.pack_into("<i", buf, off, 10 + i)
    for i, off in enumerate(offsets.RESERVE_AMMO.values()):
        struct.pack_into("<i", buf, off, 100 + i)
    name: bytes = values["name"]  # type: ignore[assignment]
    buf[offsets.NAME:offsets.NAME + len(name)] = name
    return bytes(buf)


def test_parse_player_reads_every_field() -> None:
    p = parse_player(make_buffer(), ADDRESS)
    assert p.address == ADDRESS
    assert p.name == "Harry"
    assert p.head == Vec3(10.0, 20.0, 5.5)
    assert p.feet == Vec3(10.0, 20.0, 1.0)
    assert p.yaw == pytest.approx(90.0)
    assert p.pitch == pytest.approx(-10.0)
    assert (p.health, p.armor, p.team, p.dead) == (100, 50, 1, False)
    assert p.grenades == 3
    assert p.mag_ammo == {"pistol": 10, "carbine": 11, "shotgun": 12, "smg": 13, "sniper": 14, "assault": 15}
    assert p.reserve_ammo["assault"] == 105


def test_parse_player_name_stops_at_null_and_max_length() -> None:
    # 16 non-null chars and no terminator: must not read past NAME_LENGTH.
    p = parse_player(make_buffer(name=b"A" * 16), ADDRESS)
    assert p.name == "A" * 16


def test_parse_player_dead_flag() -> None:
    assert parse_player(make_buffer(dead=1), ADDRESS).dead is True


def test_parse_player_rejects_short_buffer() -> None:
    with pytest.raises(ValueError):
        parse_player(b"\x00" * 10, ADDRESS)


@pytest.mark.parametrize("ptr, ok", [(0, False), (0x1234, False), (0x00400000, True),
                                     (0x7FFFFFFF, True), (0x80000000, False)])
def test_is_valid_pointer(ptr: int, ok: bool) -> None:
    assert is_valid_pointer(ptr) is ok


@pytest.mark.parametrize("pos, ok", [
    (Vec3(0, 0, 0), True),
    (Vec3(500.0, -300.0, 20.0), True),
    (Vec3(float("nan"), 0, 0), False),
    (Vec3(0, float("inf"), 0), False),
    (Vec3(0, 0, 1e30), False),
])
def test_is_sane_position(pos: Vec3, ok: bool) -> None:
    assert is_sane_position(pos) is ok


def test_local_player_valid_with_health_above_100() -> None:
    # The trainer can set health to 999; the local player must still count as valid.
    assert is_valid_local_player(parse_player(make_buffer(health=999), ADDRESS))


@pytest.mark.parametrize("health", [0, -20, -150])
def test_dead_local_player_is_still_valid(health: int) -> None:
    # Health can drop to 0 or below on death; a dead local player must NOT be rejected.
    assert is_valid_local_player(parse_player(make_buffer(health=health, dead=1), ADDRESS))


def test_local_player_invalid_with_garbage_position() -> None:
    assert not is_valid_local_player(parse_player(make_buffer(feet=(1e30, 0.0, 0.0)), ADDRESS))


def test_bot_health_filter_is_loose_0_to_100() -> None:
    assert is_valid_bot(parse_player(make_buffer(health=100), ADDRESS))
    assert is_valid_bot(parse_player(make_buffer(health=0), ADDRESS))
    assert not is_valid_bot(parse_player(make_buffer(health=999), ADDRESS))
    assert not is_valid_bot(parse_player(make_buffer(health=-5), ADDRESS))
