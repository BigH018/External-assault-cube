"""Dataclasses for ALL settings. Pure: no I/O, no Qt.

One shared `Settings` instance is created at startup. The UI mutates it and the controller reads it
every tick, so changes apply live. Never cache a section (e.g. `aim = settings.aimbot`) for longer
than one tick or one event handler: loading a profile replaces the section objects.

Numeric fields carry their (min, max) in field metadata via `ranged()`. The store clamps with it,
and the UI uses it for slider/spinbox limits, so ranges are defined once (values come from config.py).
Colours are "#RRGGBBAA" strings, so this module stays Qt-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any

from actrainer import config
from actrainer.input.actions import Bind, default_binds

RANGE_MIN = "min"
RANGE_MAX = "max"


def ranged(default: float, bounds: tuple[float, float]) -> Any:
    """A dataclass field with a default and (min, max) metadata."""
    return field(default=default, metadata={RANGE_MIN: bounds[0], RANGE_MAX: bounds[1]})


def field_range(cls: type, name: str) -> tuple[float, float] | None:
    """(min, max) declared for a field, or None if it has no range."""
    for f in fields(cls):
        if f.name == name and RANGE_MIN in f.metadata:
            return f.metadata[RANGE_MIN], f.metadata[RANGE_MAX]
    return None


# --- enums ----------------------------------------------------------------------

class AimTarget(str, Enum):
    HEAD = "head"
    BODY = "body"


class TargetPriority(str, Enum):
    CROSSHAIR = "crosshair"   # smallest angle from where we're looking
    DISTANCE = "distance"     # nearest in the world
    HEALTH = "health"         # lowest health


class SnaplineOrigin(str, Enum):
    BOTTOM = "bottom"
    CENTRE = "centre"


# --- sections -------------------------------------------------------------------

@dataclass(slots=True)
class GeneralSettings:
    tick_rate_hz: int = ranged(60, config.TICK_RATE_RANGE)
    overlay_fps: int = ranged(60, config.OVERLAY_FPS_RANGE)
    menu_pos: tuple[int, int] | None = None  # remembered menu window position; None = centre over game


@dataclass(slots=True)
class AimbotSettings:
    enabled: bool = False
    target: AimTarget = AimTarget.HEAD
    priority: TargetPriority = TargetPriority.CROSSHAIR
    fov_deg: float = ranged(15.0, config.AIM_FOV_RANGE)
    draw_fov: bool = True
    fov_colour: str = "#FFFFFF80"
    fov_thickness: int = ranged(1, config.LINE_THICKNESS_RANGE)
    smoothing: float = ranged(1.0, config.AIM_SMOOTHING_RANGE)
    team_check: bool = False  # off by default: in FFA modes bots share team values with you
    max_distance: float = ranged(500.0, config.AIM_MAX_DISTANCE_RANGE)


@dataclass(slots=True)
class EspSettings:
    enabled: bool = False
    box_2d: bool = True
    corner_box: bool = False
    head_circle: bool = False
    skeleton: bool = False
    thickness: int = ranged(1, config.LINE_THICKNESS_RANGE)
    enemy_colour: str = "#FF4040FF"
    team_colour: str = "#40A0FFFF"
    enemies_only: bool = False
    show_name: bool = True
    show_health_bar: bool = True
    show_health_number: bool = False
    show_distance: bool = True
    show_snaplines: bool = False
    snapline_origin: SnaplineOrigin = SnaplineOrigin.BOTTOM


@dataclass(slots=True)
class ValueSetting:
    """A single editable int (health, armour, grenades, akimbo ammo)."""

    target: int = 0
    freeze: bool = False


@dataclass(slots=True)
class AmmoSetting:
    """Magazine + reserve ammo for one weapon. Set-now and freeze apply to both."""

    mag: int = ranged(0, config.MAG_AMMO_RANGE)
    reserve: int = ranged(0, config.RESERVE_AMMO_RANGE)
    freeze: bool = False


DEFAULT_STAT_TARGETS = {"health": 100, "armor": 100, "grenades": 3, "akimbo": 20}
DEFAULT_MAG = {"pistol": 10, "carbine": 10, "shotgun": 7, "smg": 30, "sniper": 5, "assault": 20}
DEFAULT_RESERVE = 100


def _default_values() -> dict[str, ValueSetting]:
    return {v: ValueSetting(DEFAULT_STAT_TARGETS[v]) for v in config.STAT_VALUES}


def _default_ammo() -> dict[str, AmmoSetting]:
    return {w: AmmoSetting(DEFAULT_MAG[w], DEFAULT_RESERVE) for w in config.WEAPONS}


@dataclass(slots=True)
class PlayerSettings:
    values: dict[str, ValueSetting] = field(default_factory=_default_values)  # keyed by config.STAT_VALUES
    ammo: dict[str, AmmoSetting] = field(default_factory=_default_ammo)       # keyed by config.WEAPONS

    def unfreeze_all(self) -> None:
        """Turn off every freeze (used by panic)."""
        for setting in (*self.values.values(), *self.ammo.values()):
            setting.freeze = False


@dataclass(slots=True)
class KeybindSettings:
    binds: dict[str, Bind] = field(default_factory=default_binds)  # action id -> Bind


# --- root -----------------------------------------------------------------------

@dataclass(slots=True)
class Settings:
    general: GeneralSettings = field(default_factory=GeneralSettings)
    aimbot: AimbotSettings = field(default_factory=AimbotSettings)
    esp: EspSettings = field(default_factory=EspSettings)
    player: PlayerSettings = field(default_factory=PlayerSettings)
    keybinds: KeybindSettings = field(default_factory=KeybindSettings)

    def replace_with(self, other: Settings) -> None:
        """Copy every section from `other` into this instance, IN PLACE.

        Everyone holding a reference to this Settings object (UI, controller) then sees the new values.
        """
        for f in fields(self):
            setattr(self, f.name, getattr(other, f.name))
