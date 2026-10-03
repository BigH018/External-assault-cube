"""Game FOV: decide whether to write the game's field of view this tick. Pure."""

from __future__ import annotations

from actrainer import config
from actrainer.settings.models import ViewSettings


def target_fov(settings: ViewSettings) -> float:
    """The configured FOV, clamped to config.GAME_FOV_RANGE (the game itself never clamps)."""
    lo, hi = config.GAME_FOV_RANGE
    return max(lo, min(hi, settings.fov))


def plan_fov_write(current: float, settings: ViewSettings, requested: bool) -> float | None:
    """The FOV to write now (set-now request or keep-applied), or None if nothing needs writing."""
    if not (requested or settings.freeze):
        return None
    target = target_fov(settings)
    return target if abs(current - target) > config.GAME_FOV_EPSILON else None
