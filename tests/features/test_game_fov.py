"""Tests for features/game_fov.py."""

from __future__ import annotations

from actrainer import config
from actrainer.features.game_fov import plan_fov_write, target_fov
from actrainer.settings.models import ViewSettings


def test_nothing_without_request_or_keep_applied() -> None:
    assert plan_fov_write(90.0, ViewSettings(fov=110.0), requested=False) is None


def test_set_now_writes_target() -> None:
    assert plan_fov_write(90.0, ViewSettings(fov=110.0), requested=True) == 110.0


def test_keep_applied_writes_only_when_different() -> None:
    keep = ViewSettings(fov=110.0, freeze=True)
    assert plan_fov_write(90.0, keep, requested=False) == 110.0
    assert plan_fov_write(110.0, keep, requested=False) is None
    assert plan_fov_write(110.0 + config.GAME_FOV_EPSILON / 2, keep, requested=False) is None


def test_target_is_clamped() -> None:
    lo, hi = config.GAME_FOV_RANGE
    assert target_fov(ViewSettings(fov=500.0)) == hi
    assert target_fov(ViewSettings(fov=1.0)) == lo
