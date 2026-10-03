"""Aimbot: choose a target and compute the next (smoothed) view angles. Pure: no memory, no Qt.

Pipeline per tick:
    1. candidates = live bots (not dead, health > 0), minus teammates if team_check,
       within max_distance and within fov_deg of where we're looking
    2. pick one by priority (closest to crosshair / closest distance / lowest health)
    3. desired angles = calc_aim_angles(our eye, target's aim point)
    4. return smooth_angles(current view, desired, smoothing)
The controller decides WHETHER to run it (enabled + key active + game focused) and writes the result.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from actrainer.game.structs import PlayerSnapshot, Vec3
from actrainer.maths import vectors
from actrainer.maths.angles import Angles, angular_distance, calc_aim_angles, smooth_angles
from actrainer.settings.models import AimbotSettings, AimTarget, TargetPriority

# Body aim point as a fraction of the feet->head height. Head pos is the EYE (about 4.5 u above the feet
# when standing), so 0.6 is roughly mid-chest. It scales automatically when the target crouches.
BODY_HEIGHT_FRACTION = 0.6


@dataclass(frozen=True, slots=True)
class Candidate:
    """A bot that passed every filter, with the numbers used for prioritising."""

    player: PlayerSnapshot
    aim_point: Vec3
    angles: Angles        # view angles that would point exactly at aim_point
    angle_off: float      # degrees between our current view and `angles`
    distance: float       # world units from our eye to aim_point


def aim_point(player: PlayerSnapshot, target: AimTarget) -> Vec3:
    """Where on a player to aim."""
    if target is AimTarget.HEAD:
        return player.head
    return vectors.lerp(player.feet, player.head, BODY_HEIGHT_FRACTION)


def find_candidates(local: PlayerSnapshot, entities: Sequence[PlayerSnapshot],
                    settings: AimbotSettings) -> list[Candidate]:
    """Every bot the aimbot is allowed to aim at right now."""
    view = Angles(local.yaw, local.pitch)
    result: list[Candidate] = []
    for player in entities:
        if player.dead or player.health <= 0:
            continue  # ignore dead: always on
        if settings.team_check and player.team == local.team:
            continue
        point = aim_point(player, settings.target)
        dist = vectors.distance(local.head, point)
        if dist > settings.max_distance:
            continue
        angles = calc_aim_angles(local.head, point)
        off = angular_distance(view, angles)
        if off > settings.fov_deg:
            continue
        result.append(Candidate(player, point, angles, off, dist))
    return result


def _priority_key(priority: TargetPriority):  # noqa: ANN202 (returns a sort-key function)
    """Sort key for a priority. Ties are broken by angle to the crosshair, so the choice is stable."""
    if priority is TargetPriority.DISTANCE:
        return lambda c: (c.distance, c.angle_off)
    if priority is TargetPriority.HEALTH:
        return lambda c: (c.player.health, c.angle_off)
    return lambda c: (c.angle_off, c.distance)


def select_target(local: PlayerSnapshot, entities: Sequence[PlayerSnapshot],
                  settings: AimbotSettings) -> Candidate | None:
    """The best candidate by the configured priority, or None."""
    candidates = find_candidates(local, entities, settings)
    return min(candidates, key=_priority_key(settings.priority)) if candidates else None


def compute_aim(local: PlayerSnapshot, entities: Sequence[PlayerSnapshot],
                settings: AimbotSettings) -> tuple[Angles, Candidate] | None:
    """New view angles for this tick (already smoothed), plus the chosen target. None = don't aim.

    Doesn't aim while we're dead.
    """
    if local.dead:
        return None
    target = select_target(local, entities, settings)
    if target is None:
        return None
    current = Angles(local.yaw, local.pitch)
    return smooth_angles(current, target.angles, settings.smoothing), target
