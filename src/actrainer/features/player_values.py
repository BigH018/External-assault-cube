"""Player values: decide which int fields to write this tick (set-now requests + freezes). Pure.

A value id is a stat ("health", "armor", "grenades", "akimbo") or a weapon ("pistol", ...).
A weapon expands to two fields (magazine + reserve). Targets are clamped to config caps, so nothing
negative or absurd is ever written. A field is only written when it differs from the current value,
so a freeze costs nothing while the value already matches.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from actrainer import config
from actrainer.game.local_player import mag_field, reserve_field, snapshot_value
from actrainer.game.structs import PlayerSnapshot
from actrainer.settings.models import PlayerSettings


@dataclass(frozen=True, slots=True)
class ValueWrite:
    field: str   # e.g. "health", "mag:pistol"
    value: int


def _clamp(value: int, bounds: tuple[int, int]) -> int:
    return max(bounds[0], min(bounds[1], value))


def target_writes(value_id: str, settings: PlayerSettings) -> list[ValueWrite]:
    """The (clamped) target writes for one value id."""
    if value_id in settings.values:
        target = _clamp(settings.values[value_id].target, config.STAT_VALUE_RANGES[value_id])
        return [ValueWrite(value_id, target)]
    if value_id in settings.ammo:
        ammo = settings.ammo[value_id]
        return [ValueWrite(mag_field(value_id), _clamp(ammo.mag, config.MAG_AMMO_RANGE)),
                ValueWrite(reserve_field(value_id), _clamp(ammo.reserve, config.RESERVE_AMMO_RANGE))]
    raise KeyError(f"unknown value id {value_id!r}")


def describe(value_id: str, settings: PlayerSettings) -> str:
    """User-facing message for a completed set-now, e.g. "Health set to 999", "SMG ammo set to 30 / 100"."""
    values = " / ".join(str(w.value) for w in target_writes(value_id, settings))
    suffix = " ammo" if value_id in settings.ammo else ""
    return f"{config.VALUE_NAMES[value_id]}{suffix} set to {values}"


def frozen_ids(settings: PlayerSettings) -> list[str]:
    """Value ids with freeze turned on."""
    return [vid for vid, s in (*settings.values.items(), *settings.ammo.items()) if s.freeze]


def plan_writes(local: PlayerSnapshot, settings: PlayerSettings, requested: Iterable[str]) -> list[ValueWrite]:
    """Writes needed this tick: one-off requests plus every frozen value, skipping fields already correct.

    Returns nothing while the local player is dead: writing health to a dead player can confuse the
    game's death state. Freezes resume after respawn.
    """
    if local.dead:
        return []
    ids = dict.fromkeys([*requested, *frozen_ids(settings)])  # ordered and de-duplicated
    writes: list[ValueWrite] = []
    for value_id in ids:
        for write in target_writes(value_id, settings):
            if snapshot_value(local, write.field) != write.value:
                writes.append(write)
    return writes
