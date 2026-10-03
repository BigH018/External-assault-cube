"""Keybind state machine: turns 'which keys are down' into action states each tick.

Pure: the controller passes in the set of currently pressed VK codes (from winapi), so this is
fully testable without Windows.

Per tick:
    states = engine.update(pressed_vks, settings.keybinds.binds, suspended=menu_is_capturing)
    states.is_active("aimbot")   # HOLD: held right now / TOGGLE: toggled on
    states.fired("panic")        # PRESS: went down this tick
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from actrainer.input.actions import Bind, BindMode


@dataclass(frozen=True, slots=True)
class ActionStates:
    """Result of one keybind update."""

    active: frozenset[str] = field(default_factory=frozenset)  # HOLD held / TOGGLE on
    pressed: frozenset[str] = field(default_factory=frozenset)  # rising edge this tick (any mode)

    def is_active(self, action_id: str) -> bool:
        """True while a HOLD action is held, or while a TOGGLE action is toggled on."""
        return action_id in self.active

    def fired(self, action_id: str) -> bool:
        """True on the single tick the action's key went down."""
        return action_id in self.pressed


class KeybindEngine:
    """Tracks key edges and toggle states across ticks."""

    def __init__(self) -> None:
        self._previous_down: frozenset[int] = frozenset()
        self._toggled_on: set[str] = set()

    def update(self, pressed_vks: set[int] | frozenset[int], binds: Mapping[str, Bind],
               suspended: bool = False) -> ActionStates:
        """Advance one tick.

        Args:
            pressed_vks: VK codes currently held down.
            binds: action id -> Bind (usually settings.keybinds.binds).
            suspended: True while the menu captures a new bind. Key state is still tracked, so
                the captured key doesn't fire as soon as capture ends, but no actions trigger.
        """
        down = frozenset(pressed_vks)
        just_pressed = down - self._previous_down  # rising edges: down now, not down last tick
        self._previous_down = down
        if suspended:
            return ActionStates(frozenset(self._toggled_on & set(binds)), frozenset())

        active: set[str] = set()
        fired: set[str] = set()
        for action_id, bind in binds.items():
            if bind.key is None:
                continue
            edge = bind.key in just_pressed
            if edge:
                fired.add(action_id)
            if bind.mode is BindMode.HOLD:
                if bind.key in down:
                    active.add(action_id)
            elif bind.mode is BindMode.TOGGLE:
                if edge:
                    self._toggled_on ^= {action_id}  # flip
                if action_id in self._toggled_on:
                    active.add(action_id)
        return ActionStates(frozenset(active), frozenset(fired))

    def reset_toggles(self) -> None:
        """Turn every TOGGLE action off (used by panic)."""
        self._toggled_on.clear()


def find_conflicts(binds: Mapping[str, Bind]) -> dict[int, list[str]]:
    """Keys bound to more than one action: {vk: [action ids]}. Unbound actions are ignored."""
    by_key: dict[int, list[str]] = {}
    for action_id, bind in binds.items():
        if bind.key is not None:
            by_key.setdefault(bind.key, []).append(action_id)
    return {vk: ids for vk, ids in by_key.items() if len(ids) > 1}
