"""Registry of every bindable action, plus the Bind/BindMode types.

This lives in its own module (not keybinds.py) so settings/models.py can build default binds
from it without a circular import: models -> actions, keybinds -> actions.

To add a bindable action: add an ActionDef to `_build_actions()` below, then handle it in
app/controller.py. The Keybinds tab and the default profile pick it up automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from actrainer import config
from actrainer.input.keys import VK_END, VK_INSERT, VK_RBUTTON


class BindMode(str, Enum):
    """How a bind turns key presses into an action state."""

    HOLD = "hold"      # active while the key is held
    TOGGLE = "toggle"  # each press flips active on/off
    PRESS = "press"    # fires once, on the tick the key goes down


@dataclass(slots=True)
class Bind:
    """A key assignment for one action. key=None means unbound."""

    key: int | None = None
    mode: BindMode = BindMode.PRESS


@dataclass(frozen=True, slots=True)
class ActionDef:
    """Static description of a bindable action."""

    id: str
    label: str
    category: str
    allowed_modes: tuple[BindMode, ...]
    default_mode: BindMode
    default_key: int | None = None


PRESS_ONLY = (BindMode.PRESS,)
HOLD_OR_TOGGLE = (BindMode.HOLD, BindMode.TOGGLE)

CATEGORY_GENERAL = "General"
CATEGORY_AIMBOT = "Aimbot"
CATEGORY_ESP = "ESP"
CATEGORY_PLAYER = "Player"

# Well-known action ids used by the controller.
MENU_TOGGLE = "menu_toggle"
PANIC = "panic"
QUIT = "quit"
AIMBOT_ACTIVATE = "aimbot"
AIMBOT_ENABLE_TOGGLE = "aimbot_enable_toggle"
ESP_TOGGLE = "esp_toggle"


def set_action_id(value_id: str) -> str:
    """Action id for 'set <value> now' (value_id is a STAT_VALUES entry or a weapon)."""
    return f"set_{value_id}"


def freeze_action_id(value_id: str) -> str:
    """Action id for 'toggle freeze on <value>'."""
    return f"freeze_{value_id}"


def _value_label(value_id: str) -> str:
    name = config.VALUE_NAMES[value_id]
    return f"{name} ammo" if value_id in config.WEAPONS else name


def _build_actions() -> tuple[ActionDef, ...]:
    actions = [
        ActionDef(MENU_TOGGLE, "Show/hide menu", CATEGORY_GENERAL, PRESS_ONLY, BindMode.PRESS, VK_INSERT),
        ActionDef(PANIC, "Panic (disable everything)", CATEGORY_GENERAL, PRESS_ONLY, BindMode.PRESS, VK_END),
        ActionDef(QUIT, "Quit trainer", CATEGORY_GENERAL, PRESS_ONLY, BindMode.PRESS, None),
        ActionDef(AIMBOT_ACTIVATE, "Aimbot activation", CATEGORY_AIMBOT, HOLD_OR_TOGGLE, BindMode.HOLD, VK_RBUTTON),
        ActionDef(AIMBOT_ENABLE_TOGGLE, "Aimbot enable on/off", CATEGORY_AIMBOT, PRESS_ONLY, BindMode.PRESS, None),
        ActionDef(ESP_TOGGLE, "ESP on/off", CATEGORY_ESP, PRESS_ONLY, BindMode.PRESS, None),
    ]
    for value_id in (*config.STAT_VALUES, *config.WEAPONS):
        label = _value_label(value_id)
        actions.append(ActionDef(set_action_id(value_id), f"Set {label} now", CATEGORY_PLAYER,
                                 PRESS_ONLY, BindMode.PRESS))
        actions.append(ActionDef(freeze_action_id(value_id), f"Freeze {label} on/off", CATEGORY_PLAYER,
                                 PRESS_ONLY, BindMode.PRESS))
    return tuple(actions)


ACTIONS: tuple[ActionDef, ...] = _build_actions()
ACTIONS_BY_ID: dict[str, ActionDef] = {a.id: a for a in ACTIONS}


def default_binds() -> dict[str, Bind]:
    """A fresh dict of every action's default bind (new objects each call)."""
    return {a.id: Bind(a.default_key, a.default_mode) for a in ACTIONS}
