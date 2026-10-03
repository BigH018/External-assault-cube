"""Tests for settings/store.py: serialisation, validation, migration and profile files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from actrainer import config
from actrainer.input.actions import AIMBOT_ACTIVATE, MENU_TOGGLE, PANIC, Bind, BindMode
from actrainer.input.keys import VK_INSERT
from actrainer.settings import store
from actrainer.settings.models import AimTarget, Settings, TargetPriority
from actrainer.settings.store import ProfileError, ProfileStore, default_settings, from_dict, to_dict


# --- serialisation ------------------------------------------------------------------

def test_round_trip_defaults() -> None:
    settings, warnings = from_dict(to_dict(default_settings()))
    assert settings == default_settings()
    assert warnings == []


def test_round_trip_changed_values() -> None:
    s = default_settings()
    s.aimbot.enabled = True
    s.aimbot.target = AimTarget.BODY
    s.aimbot.priority = TargetPriority.HEALTH
    s.aimbot.fov_deg = 33.5
    s.esp.enemy_colour = "#12345678"
    s.general.menu_pos = (100, 200)
    s.player.values["health"].target = 999
    s.player.ammo["sniper"].freeze = True
    s.keybinds.binds[PANIC] = Bind(0x74, BindMode.PRESS)
    loaded, warnings = from_dict(json.loads(json.dumps(to_dict(s))))
    assert loaded == s and warnings == []


def test_json_uses_readable_names() -> None:
    data = to_dict(default_settings())
    assert data["schema_version"] == store.CURRENT_SCHEMA_VERSION
    assert data["keybinds"][MENU_TOGGLE] == {"key": "INSERT", "mode": "press"}
    assert data["aimbot"]["target"] == "head"
    assert data["general"]["menu_pos"] is None


# --- forgiving loading ----------------------------------------------------------------

def test_missing_sections_and_keys_use_defaults() -> None:
    settings, warnings = from_dict({"schema_version": 1, "aimbot": {"fov_deg": 20.0}})
    assert settings.aimbot.fov_deg == 20.0
    assert settings.esp == default_settings().esp
    assert warnings == []


def test_unknown_keys_are_ignored_with_warning() -> None:
    settings, warnings = from_dict({"aimbot": {"wallhack": True}, "mystery": {}, "keybinds": {"fly": {}}})
    assert settings == default_settings()
    assert len(warnings) == 3


@pytest.mark.parametrize("field, bad", [("enabled", "yes"), ("fov_deg", "wide"), ("target", "feet"),
                                        ("fov_colour", "red"), ("fov_deg", True), ("fov_deg", float("nan"))])
def test_bad_values_fall_back_to_default(field: str, bad: object) -> None:
    settings, warnings = from_dict({"aimbot": {field: bad}})
    assert getattr(settings.aimbot, field) == getattr(default_settings().aimbot, field)
    assert warnings


def test_numbers_are_clamped_to_range() -> None:
    settings, warnings = from_dict({"aimbot": {"fov_deg": 5000, "smoothing": -3},
                                    "general": {"tick_rate_hz": 1}})
    assert settings.aimbot.fov_deg == config.AIM_FOV_RANGE[1]
    assert settings.aimbot.smoothing == config.AIM_SMOOTHING_RANGE[0]
    assert settings.general.tick_rate_hz == config.TICK_RATE_RANGE[0]
    assert len(warnings) == 3


def test_stat_values_use_per_stat_caps() -> None:
    settings, _ = from_dict({"player": {"values": {"health": {"target": 5000}, "grenades": {"target": -4}}}})
    assert settings.player.values["health"].target == config.STAT_VALUE_RANGES["health"][1]
    assert settings.player.values["grenades"].target == 0


def test_ammo_clamped_and_partial() -> None:
    settings, _ = from_dict({"player": {"ammo": {"smg": {"mag": -10, "freeze": True}}}})
    assert settings.player.ammo["smg"].mag == 0
    assert settings.player.ammo["smg"].freeze is True
    assert settings.player.ammo["smg"].reserve == default_settings().player.ammo["smg"].reserve


def test_colour_without_alpha_gets_opaque_alpha() -> None:
    settings, _ = from_dict({"esp": {"enemy_colour": "#ff0000"}})
    assert settings.esp.enemy_colour == "#FF0000FF"


def test_menu_pos_validation() -> None:
    assert from_dict({"general": {"menu_pos": [10, 20]}})[0].general.menu_pos == (10, 20)
    assert from_dict({"general": {"menu_pos": None}})[0].general.menu_pos is None
    assert from_dict({"general": {"menu_pos": [1, 2, 3]}})[0].general.menu_pos is None


def test_keybind_loading() -> None:
    settings, warnings = from_dict({"keybinds": {
        MENU_TOGGLE: {"key": "F1", "mode": "press"},
        PANIC: {"key": "NOPE", "mode": "press"},           # unknown key -> unbound
        AIMBOT_ACTIVATE: {"key": "MOUSE5", "mode": "press"},  # press not allowed for aimbot -> hold
    }})
    binds = settings.keybinds.binds
    assert binds[MENU_TOGGLE] == Bind(0x70, BindMode.PRESS)
    assert binds[PANIC].key is None
    assert binds[AIMBOT_ACTIVATE] == Bind(0x06, BindMode.HOLD)
    assert len(warnings) == 2


def test_explicitly_unbound_key_has_no_warning() -> None:
    settings, warnings = from_dict({"keybinds": {MENU_TOGGLE: {"key": None, "mode": "press"}}})
    assert settings.keybinds.binds[MENU_TOGGLE].key is None
    assert warnings == []


def test_not_an_object() -> None:
    settings, warnings = from_dict([1, 2, 3])
    assert settings == default_settings() and warnings


# --- versioning ---------------------------------------------------------------------

def test_migration_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    def v1_to_v2(data: dict) -> dict:
        data = dict(data)
        data["aimbot"] = {"fov_deg": data.pop("old_fov")}
        data["schema_version"] = 2
        return data
    monkeypatch.setattr(store, "CURRENT_SCHEMA_VERSION", 2)
    monkeypatch.setitem(store.MIGRATIONS, 1, v1_to_v2)
    settings, warnings = from_dict({"schema_version": 1, "old_fov": 77.0})
    assert settings.aimbot.fov_deg == 77.0 and warnings == []


def test_newer_schema_loads_best_effort() -> None:
    settings, warnings = from_dict({"schema_version": 99, "aimbot": {"fov_deg": 12.0}})
    assert settings.aimbot.fov_deg == 12.0
    assert any("newer" in w for w in warnings)


# --- profile files -------------------------------------------------------------------

@pytest.fixture
def profiles(tmp_path: Path) -> ProfileStore:
    return ProfileStore(tmp_path / "profiles")


def test_save_load_list(profiles: ProfileStore) -> None:
    s = default_settings()
    s.aimbot.fov_deg = 25.0
    profiles.save("my aim", s)
    profiles.save("Zeta", default_settings())
    profiles.save(config.DEFAULT_PROFILE, default_settings(), allow_read_only=True)
    assert profiles.list_profiles() == [config.DEFAULT_PROFILE, "my aim", "Zeta"]
    assert profiles.load("my aim").aimbot.fov_deg == 25.0


def test_save_leaves_no_temp_file(profiles: ProfileStore) -> None:
    profiles.save("a", default_settings())
    assert [p.name for p in profiles.directory.iterdir()] == ["a.json"]


@pytest.mark.parametrize("name", ["", "   ", "../evil", "a/b", ".hidden", "x" * 41, "con:", "CON", "nul", "com1"])
def test_invalid_names_rejected(profiles: ProfileStore, name: str) -> None:
    with pytest.raises(ProfileError):
        profiles.save(name, default_settings())


def test_default_profile_is_read_only(profiles: ProfileStore) -> None:
    profiles.save(config.DEFAULT_PROFILE, default_settings(), allow_read_only=True)
    with pytest.raises(ProfileError):
        profiles.save(config.DEFAULT_PROFILE, default_settings())
    with pytest.raises(ProfileError):
        profiles.delete(config.DEFAULT_PROFILE)
    with pytest.raises(ProfileError):
        profiles.rename(config.DEFAULT_PROFILE, "other")


def test_rename_and_delete(profiles: ProfileStore) -> None:
    profiles.save("one", default_settings())
    profiles.set_last_profile("one")
    profiles.rename("one", "two")
    assert profiles.list_profiles() == ["two"]
    assert profiles.get_last_profile() == "two"  # marker follows the rename
    profiles.save("three", default_settings())
    with pytest.raises(ProfileError):
        profiles.rename("two", "three")  # target exists
    profiles.delete("two")
    assert profiles.list_profiles() == ["three"]
    with pytest.raises(ProfileError):
        profiles.delete("two")


def test_load_missing_or_corrupt(profiles: ProfileStore) -> None:
    with pytest.raises(ProfileError):
        profiles.load("nope")
    profiles.directory.mkdir(parents=True)
    (profiles.directory / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ProfileError):
        profiles.load("broken")


def test_load_records_warnings(profiles: ProfileStore) -> None:
    profiles.directory.mkdir(parents=True)
    (profiles.directory / "odd.json").write_text(json.dumps({"aimbot": {"fov_deg": 9999}}), encoding="utf-8")
    profiles.load("odd")
    assert profiles.last_warnings


def test_startup_prefers_last_then_default_then_builtin(profiles: ProfileStore) -> None:
    assert profiles.load_startup() == (config.DEFAULT_PROFILE, default_settings())  # nothing on disk

    d = default_settings()
    d.aimbot.fov_deg = 11.0
    profiles.save(config.DEFAULT_PROFILE, d, allow_read_only=True)
    assert profiles.load_startup()[1].aimbot.fov_deg == 11.0

    mine = default_settings()
    mine.aimbot.fov_deg = 22.0
    profiles.save("mine", mine)
    profiles.set_last_profile("mine")
    assert profiles.load_startup() == ("mine", mine)


def test_startup_skips_corrupt_last_profile(profiles: ProfileStore) -> None:
    profiles.directory.mkdir(parents=True)
    (profiles.directory / "bad.json").write_text("{{{", encoding="utf-8")
    profiles.set_last_profile("bad")
    name, settings = profiles.load_startup()
    assert name == config.DEFAULT_PROFILE and settings == default_settings()


# --- the committed default profile ---------------------------------------------------------

def test_committed_default_profile_matches_code_defaults() -> None:
    path = config.PROFILES_DIR / f"{config.DEFAULT_PROFILE}{config.PROFILE_EXTENSION}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == to_dict(default_settings()), "regenerate profiles/default.json (see CLAUDE.md §7)"


def test_menu_toggle_default_key() -> None:
    assert Settings().keybinds.binds[MENU_TOGGLE].key == VK_INSERT
