"""Read the entity list: every other player (bots) as a list of PlayerSnapshots.

Memory layout (see offsets.py):
    module + ENTITY_LIST_PTR -> pointer to an array of uint32 entity pointers
    module + PLAYER_COUNT    -> number of slots in use (includes the local player's slot)

Slot 0 is usually null (it stands for the local player). Bad slots are skipped, never fatal.
"""

from __future__ import annotations

import logging
import struct

from actrainer import config, offsets
from actrainer.game.player import is_valid_bot, is_valid_pointer, read_player
from actrainer.game.structs import PlayerSnapshot
from actrainer.memory.process import GameProcess, MemoryAccessError

log = logging.getLogger(__name__)


def read_player_count(proc: GameProcess) -> int:
    """Number of slots in the entity list, clamped to 0..config.MAX_ENTITIES.

    Raises:
        MemoryAccessError: if the read fails.
    """
    count = proc.read_i32(proc.module_base + offsets.PLAYER_COUNT)
    if not 0 <= count <= config.MAX_ENTITIES:
        log.debug("player count %d out of range, treating as 0", count)
        return 0
    return count


def read_entity_pointers(proc: GameProcess) -> list[int]:
    """Read every slot of the entity pointer array in one call (raw values, may include nulls).

    Raises:
        MemoryAccessError: if a read fails.
    """
    count = read_player_count(proc)
    list_address = proc.read_u32(proc.module_base + offsets.ENTITY_LIST_PTR)
    if count == 0 or not is_valid_pointer(list_address):
        return []
    # The array holds 32-bit pointers, so read count * 4 bytes and unpack them as uint32.
    raw = proc.read_bytes(list_address, count * offsets.POINTER_SIZE)
    return list(struct.unpack(f"<{count}I", raw))


def read_entities(proc: GameProcess, local_address: int | None,
                  include_dead: bool = False) -> list[PlayerSnapshot]:
    """Read every valid bot.

    Skips null/garbage pointers, the local player, entries that fail the sanity check and
    (unless include_dead) dead bots. A single bad entity is logged and skipped. It never
    aborts the whole list.

    Args:
        proc: an attached GameProcess.
        local_address: the local player's address, so it can be excluded (None if unknown).
        include_dead: keep dead bots (useful for debugging).

    Raises:
        MemoryAccessError: only if the list itself can't be read (e.g. the game closed).
    """
    players: list[PlayerSnapshot] = []
    for slot, ptr in enumerate(read_entity_pointers(proc)):
        if not is_valid_pointer(ptr) or ptr == local_address:
            continue
        try:
            player = read_player(proc, ptr)
        except MemoryAccessError as exc:
            log.debug("entity slot %d (0x%08X) unreadable: %s", slot, ptr, exc)
            continue
        if not is_valid_bot(player):
            log.debug("entity slot %d (0x%08X) failed sanity check", slot, ptr)
            continue
        if player.dead and not include_dead:
            continue
        players.append(player)
    return players
