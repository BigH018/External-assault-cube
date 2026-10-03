"""Find and read the local player, and write its view angles.

Value writes (health, ammo...) come in Phase 7.
"""

from __future__ import annotations

import logging
import struct

from actrainer import offsets
from actrainer.maths.angles import Angles
from actrainer.game.player import is_valid_local_player, is_valid_pointer, read_player
from actrainer.game.structs import PlayerSnapshot
from actrainer.memory.process import GameProcess

log = logging.getLogger(__name__)


def get_local_player_address(proc: GameProcess) -> int | None:
    """Follow the static local-player pointer: module base + LOCAL_PLAYER_PTR -> player address.

    The static slot holds a POINTER, so we read a uint32 (32-bit game) and use it as the address.
    Returns None when the slot is null or garbage (e.g. in the main menu, between matches).

    Raises:
        MemoryAccessError: if the read itself fails.
    """
    ptr = proc.read_u32(proc.module_base + offsets.LOCAL_PLAYER_PTR)
    return ptr if is_valid_pointer(ptr) else None


def read_local_player(proc: GameProcess) -> PlayerSnapshot | None:
    """Read the local player, or None if there isn't a valid one right now.

    Raises:
        MemoryAccessError: if a read fails (e.g. the game closed).
    """
    address = get_local_player_address(proc)
    if address is None:
        return None
    player = read_player(proc, address)
    if not is_valid_local_player(player):
        log.debug("local player at 0x%08X failed sanity check", address)
        return None
    return player


# Yaw (0x34) and pitch (0x38) are adjacent floats, so both go in ONE 8-byte write. The game can then
# never see a new yaw paired with an old pitch.
_YAW_PITCH = struct.Struct("<2f")
assert offsets.VIEW_PITCH == offsets.VIEW_YAW + 4, "yaw and pitch must be adjacent for the combined write"


def write_view_angles(proc: GameProcess, player_address: int, angles: Angles) -> None:
    """Point the local player's view at `angles` (AC degrees).

    Raises:
        MemoryAccessError: if the write fails.
    """
    proc.write_bytes(player_address + offsets.VIEW_YAW, _YAW_PITCH.pack(angles.yaw, angles.pitch))


# --- editable int fields --------------------------------------------------------------
# Features name fields with plain ids ("health", "mag:pistol", "reserve:pistol"). Only this module
# knows which offset each id lives at.

def mag_field(weapon: str) -> str:
    """Field id for a weapon's magazine ammo."""
    return f"mag:{weapon}"


def reserve_field(weapon: str) -> str:
    """Field id for a weapon's reserve ammo."""
    return f"reserve:{weapon}"


VALUE_FIELD_OFFSETS: dict[str, int] = {
    "health": offsets.HEALTH,
    "armor": offsets.ARMOR,
    "grenades": offsets.GRENADES,
    "akimbo": offsets.AKIMBO_AMMO,
    **{mag_field(w): off for w, off in offsets.MAG_AMMO.items()},
    **{reserve_field(w): off for w, off in offsets.RESERVE_AMMO.items()},
}


def snapshot_value(player: PlayerSnapshot, field: str) -> int:
    """The current value of an editable field, taken from an already-read snapshot (no memory access)."""
    if field.startswith("mag:"):
        return player.mag_ammo[field[len("mag:"):]]
    if field.startswith("reserve:"):
        return player.reserve_ammo[field[len("reserve:"):]]
    return {"health": player.health, "armor": player.armor,
            "grenades": player.grenades, "akimbo": player.akimbo_ammo}[field]


def write_player_value(proc: GameProcess, player_address: int, field: str, value: int) -> None:
    """Write one editable int field of the local player.

    Raises:
        KeyError: unknown field id.
        MemoryAccessError: if the write fails.
    """
    proc.write_i32(player_address + VALUE_FIELD_OFFSETS[field], value)
