"""Find and read the local player.

Phase 1 is read-only. View-angle writes come in Phase 6 and value writes in Phase 7.
"""

from __future__ import annotations

import logging

from actrainer import offsets
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
