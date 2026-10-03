"""Controller status shown in the menu (pure data)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ControllerStatus:
    attached: bool = False
    pid: int = 0
    module_base: int = 0
    exe_version: str | None = None   # None when the exe has no version resource (true for AC 1.3.0.2)
    offsets_ok: bool = False         # local player pointer resolves to a sane player
    in_match: bool = False           # same as offsets_ok right now; kept separate for clarity in the UI
    entity_count: int = 0            # valid bots (Phase 6+), or raw player count before that
    tick_rate: float = 0.0           # measured ticks per second
    game_focused: bool = False
    game_fov: float = 0.0            # current game FOV in degrees (0 if not in a match)
    player_values: dict[str, int] = field(default_factory=dict)  # field id -> current in-game value (empty if not in a match)
