"""One call per tick that reads everything the features need into a GameState."""

from __future__ import annotations

from actrainer.game.entities import read_entities
from actrainer.game.local_player import read_local_player
from actrainer.game.structs import GameState
from actrainer.game.view import read_fov, read_view_matrix
from actrainer.memory.process import GameProcess


def read_game_state(proc: GameProcess) -> GameState | None:
    """Read the local player, every live bot, the view matrix and the FOV.

    Returns None when there's no valid local player (main menu, loading, between matches).

    Raises:
        MemoryAccessError: if a read fails (the controller logs it and skips the tick).
    """
    local = read_local_player(proc)
    if local is None:
        return None
    entities = read_entities(proc, local.address)  # dead bots excluded: features always ignore them
    return GameState(local=local, entities=tuple(entities),
                     view_matrix=read_view_matrix(proc), fov=read_fov(proc))
