"""Tests for features/player_values.py and the game-layer field mapping."""

from __future__ import annotations

import pytest

from actrainer import config, offsets
from actrainer.features.player_values import ValueWrite, describe, frozen_ids, plan_writes, target_writes
from actrainer.game.local_player import VALUE_FIELD_OFFSETS, mag_field, reserve_field, snapshot_value
from actrainer.game.player import parse_player
from actrainer.settings.models import PlayerSettings
from helpers.fake_game import make_player_buffer

# make_player_buffer: health 100, armor 50, grenades 3, akimbo 0, mag 10.., reserve 100..
LOCAL = parse_player(make_player_buffer(), 0x1000)


def test_every_field_has_an_offset_and_reads_from_snapshot() -> None:
    expected = {"health", "armor", "grenades", "akimbo",
                *(mag_field(w) for w in config.WEAPONS), *(reserve_field(w) for w in config.WEAPONS)}
    assert set(VALUE_FIELD_OFFSETS) == expected
    assert VALUE_FIELD_OFFSETS["health"] == offsets.HEALTH
    assert VALUE_FIELD_OFFSETS[mag_field("sniper")] == offsets.MAG_AMMO["sniper"]
    assert snapshot_value(LOCAL, "armor") == 50
    assert snapshot_value(LOCAL, mag_field("pistol")) == 10
    assert snapshot_value(LOCAL, reserve_field("carbine")) == 101


def test_target_writes_for_stat_and_weapon() -> None:
    s = PlayerSettings()
    s.values["health"].target = 999
    s.ammo["smg"].mag, s.ammo["smg"].reserve = 30, 200
    assert target_writes("health", s) == [ValueWrite("health", 999)]
    assert target_writes("smg", s) == [ValueWrite("mag:smg", 30), ValueWrite("reserve:smg", 200)]
    with pytest.raises(KeyError):
        target_writes("jetpack", s)


def test_targets_are_clamped_never_negative() -> None:
    s = PlayerSettings()
    s.values["health"].target = -50          # bypassing the UI
    s.values["grenades"].target = 10_000
    s.ammo["pistol"].mag = -1
    assert target_writes("health", s)[0].value == config.STAT_VALUE_RANGES["health"][0]
    assert target_writes("grenades", s)[0].value == config.STAT_VALUE_RANGES["grenades"][1]
    assert target_writes("pistol", s)[0].value == 0


def test_plan_writes_set_now_only_changed_fields() -> None:
    s = PlayerSettings()
    s.values["health"].target = 100           # already 100 -> no write
    s.values["armor"].target = 100            # currently 50 -> write
    assert plan_writes(LOCAL, s, ["health", "armor"]) == [ValueWrite("armor", 100)]


def test_plan_writes_includes_frozen_values() -> None:
    s = PlayerSettings()
    s.values["grenades"].target = 9
    s.values["grenades"].freeze = True
    s.ammo["sniper"].mag = 5
    s.ammo["sniper"].freeze = True
    writes = plan_writes(LOCAL, s, [])
    assert ValueWrite("grenades", 9) in writes
    assert ValueWrite("mag:sniper", 5) in writes
    assert frozen_ids(s) == ["grenades", "sniper"]


def test_requested_and_frozen_not_duplicated() -> None:
    s = PlayerSettings()
    s.values["armor"].target = 77
    s.values["armor"].freeze = True
    assert plan_writes(LOCAL, s, ["armor"]) == [ValueWrite("armor", 77)]


def test_nothing_written_while_dead() -> None:
    dead = parse_player(make_player_buffer(dead=1, health=-20), 0x1000)
    s = PlayerSettings()
    s.values["health"].freeze = True
    assert plan_writes(dead, s, ["armor"]) == []


def test_describe() -> None:
    s = PlayerSettings()
    s.values["health"].target = 999
    assert describe("health", s) == "Health set to 999"
    assert describe("smg", s) == "SMG ammo set to 30 / 100"
