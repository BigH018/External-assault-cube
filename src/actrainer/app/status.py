"""Controller status shown in the menu (pure data)."""

from __future__ import annotations

from dataclasses import dataclass


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
