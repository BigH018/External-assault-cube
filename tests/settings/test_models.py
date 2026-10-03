"""Tests for settings/models.py."""

from __future__ import annotations

from dataclasses import fields

from actrainer import config, offsets
from actrainer.settings.models import (
    RANGE_MAX,
    RANGE_MIN,
    AimbotSettings,
    AmmoSetting,
    EspSettings,
    GeneralSettings,
    Settings,
    field_range,
)


def test_weapons_match_offsets() -> None:
    assert set(config.WEAPONS) == set(offsets.MAG_AMMO) == set(offsets.RESERVE_AMMO)


def test_defaults_are_inside_their_ranges() -> None:
    for cls in (GeneralSettings, AimbotSettings, EspSettings, AmmoSetting):
        obj = cls()
        for f in fields(cls):
            if RANGE_MIN in f.metadata:
                assert f.metadata[RANGE_MIN] <= getattr(obj, f.name) <= f.metadata[RANGE_MAX], f.name


def test_default_stat_targets_inside_caps() -> None:
    for stat, setting in Settings().player.values.items():
        lo, hi = config.STAT_VALUE_RANGES[stat]
        assert lo <= setting.target <= hi


def test_field_range_lookup() -> None:
    assert field_range(AimbotSettings, "fov_deg") == config.AIM_FOV_RANGE
    assert field_range(AimbotSettings, "enabled") is None


def test_player_has_every_value_and_weapon() -> None:
    s = Settings()
    assert set(s.player.values) == set(config.STAT_VALUES)
    assert set(s.player.ammo) == set(config.WEAPONS)


def test_unfreeze_all() -> None:
    s = Settings()
    s.player.values["health"].freeze = True
    s.player.ammo["sniper"].freeze = True
    s.player.unfreeze_all()
    assert not any(v.freeze for v in (*s.player.values.values(), *s.player.ammo.values()))


def test_replace_with_keeps_identity() -> None:
    shared = Settings()
    other = Settings()
    other.aimbot.fov_deg = 42.0
    shared.replace_with(other)
    assert shared.aimbot.fov_deg == 42.0


def test_instances_do_not_share_mutable_defaults() -> None:
    a, b = Settings(), Settings()
    a.player.values["health"].target = 5
    assert b.player.values["health"].target == 100
