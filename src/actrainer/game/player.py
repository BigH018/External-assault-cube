"""Read and validate a player struct. Shared by the local player and the entity list.

The struct is read in ONE cross-process call (offsets.PLAYER_READ_SIZE bytes), then every field
is unpacked from that local buffer. `parse_player` is pure, so it is unit-tested with fake bytes.
"""

from __future__ import annotations

import math
import struct

from actrainer import config, offsets
from actrainer.game.structs import PlayerSnapshot, Vec3
from actrainer.memory.process import GameProcess

_VEC3 = struct.Struct("<3f")
_F32 = struct.Struct("<f")
_I32 = struct.Struct("<i")


def _vec3_at(buf: bytes, offset: int) -> Vec3:
    return Vec3(*_VEC3.unpack_from(buf, offset))


def _f32_at(buf: bytes, offset: int) -> float:
    return _F32.unpack_from(buf, offset)[0]


def _i32_at(buf: bytes, offset: int) -> int:
    return _I32.unpack_from(buf, offset)[0]


def _name_at(buf: bytes, offset: int) -> str:
    # char[16]: take bytes up to the first null terminator.
    raw = buf[offset:offset + offsets.NAME_LENGTH].split(b"\x00", 1)[0]
    return raw.decode(config.NAME_ENCODING)


def parse_player(buf: bytes, address: int) -> PlayerSnapshot:
    """Build a PlayerSnapshot from a raw player struct buffer.

    Args:
        buf: at least offsets.PLAYER_READ_SIZE bytes, starting at the player struct.
        address: where the struct lives in game memory (kept for later writes).

    Raises:
        ValueError: if the buffer is too short.
    """
    if len(buf) < offsets.PLAYER_READ_SIZE:
        raise ValueError(f"player buffer too short: {len(buf)} < {offsets.PLAYER_READ_SIZE}")
    return PlayerSnapshot(
        address=address,
        name=_name_at(buf, offsets.NAME),
        head=_vec3_at(buf, offsets.HEAD_POS),
        feet=_vec3_at(buf, offsets.FEET_POS),
        yaw=_f32_at(buf, offsets.VIEW_YAW),
        pitch=_f32_at(buf, offsets.VIEW_PITCH),
        health=_i32_at(buf, offsets.HEALTH),
        armor=_i32_at(buf, offsets.ARMOR),
        team=_i32_at(buf, offsets.TEAM),
        dead=_i32_at(buf, offsets.DEAD) != 0,
        mag_ammo={w: _i32_at(buf, off) for w, off in offsets.MAG_AMMO.items()},
        reserve_ammo={w: _i32_at(buf, off) for w, off in offsets.RESERVE_AMMO.items()},
        grenades=_i32_at(buf, offsets.GRENADES),
        akimbo_ammo=_i32_at(buf, offsets.AKIMBO_AMMO),
    )


def read_player(proc: GameProcess, address: int) -> PlayerSnapshot:
    """Read one player struct from game memory.

    Raises:
        MemoryAccessError: if the read fails.
    """
    return parse_player(proc.read_bytes(address, offsets.PLAYER_READ_SIZE), address)


# --- validity checks (pure) -----------------------------------------------------


def is_valid_pointer(ptr: int) -> bool:
    """True if `ptr` looks like a real 32-bit user-space address (not null or garbage)."""
    return config.MIN_VALID_POINTER <= ptr <= config.MAX_VALID_POINTER


def is_sane_position(pos: Vec3) -> bool:
    """True if every coordinate is a finite number inside the world bounds.

    Garbage memory decodes as huge floats, NaN or inf, so this catches most bad reads.
    """
    return all(math.isfinite(c) and abs(c) <= config.WORLD_COORD_LIMIT for c in (pos.x, pos.y, pos.z))


def is_valid_local_player(player: PlayerSnapshot) -> bool:
    """Validity for the LOCAL player: sane positions and a very wide health range.

    Deliberately NOT a 0..100 health check: the trainer can set health to e.g. 999
    (see CLAUDE.md §6 "Validity checks").
    """
    return (is_sane_position(player.head)
            and is_sane_position(player.feet)
            and config.LOCAL_HEALTH_SANE_MIN <= player.health <= config.LOCAL_HEALTH_SANE_MAX)


def is_valid_bot(player: PlayerSnapshot) -> bool:
    """Validity for a BOT entry: sane positions plus a loose 0..100 health filter."""
    return (is_sane_position(player.head)
            and is_sane_position(player.feet)
            and config.BOT_HEALTH_MIN <= player.health <= config.BOT_HEALTH_MAX)
