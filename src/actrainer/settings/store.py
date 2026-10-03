"""JSON profiles: load/save/list/rename/delete, defaults, validation and schema versioning.

Profile format (profiles/<name>.json):
    {
      "schema_version": 1,
      "general":  {...}, "aimbot": {...}, "esp": {...}, "view": {"fov": 90.0, "freeze": false},
      "player":   {"values": {"health": {"target": 100, "freeze": false}, ...},
                   "ammo":   {"pistol": {"mag": 10, "reserve": 100, "freeze": false}, ...}},
      "keybinds": {"menu_toggle": {"key": "INSERT", "mode": "press"}, ...}
    }

Loading never fails on bad content: unknown keys are ignored, missing keys keep their defaults,
wrong types / bad enums / bad colours fall back to the default, and numbers are clamped to their
range. Every problem is logged and collected in `ProfileStore.last_warnings` (the UI can show them).
Only an unreadable file or invalid JSON raises ProfileError.

Versioning: bump CURRENT_SCHEMA_VERSION and add MIGRATIONS[old] = fn(dict) -> dict whenever a
change would load wrongly from an old profile (rename/move/re-meaning of a field). Adding a field
with a sensible default needs no migration.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import typing
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from types import UnionType
from typing import Any

from actrainer import config
from actrainer.input import keys
from actrainer.input.actions import ACTIONS_BY_ID, Bind, BindMode
from actrainer.settings.models import (
    RANGE_MAX,
    RANGE_MIN,
    AmmoSetting,
    PlayerSettings,
    Settings,
    ValueSetting,
)

log = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1
SCHEMA_KEY = "schema_version"

# from_version -> function that upgrades a profile dict to from_version + 1.
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}

_FLAT_SECTIONS = ("general", "aimbot", "esp", "view")
_COLOUR_RE = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]*$")
# Windows device names can't be used as file names (even with an extension).
_RESERVED_NAMES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
_OPAQUE_ALPHA = "FF"
_JSON_INDENT = 2


class ProfileError(Exception):
    """A profile operation failed (bad name, missing/read-only profile, unreadable file, invalid JSON)."""


def default_settings() -> Settings:
    """Fresh built-in defaults (what "reset to defaults" uses)."""
    return Settings()


# --- serialisation ---------------------------------------------------------------

def _plain(value: Any) -> Any:
    """Convert a field value to a JSON-friendly value."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    if is_dataclass(value):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    return value


def to_dict(settings: Settings) -> dict[str, Any]:
    """Settings -> JSON-ready dict (keys as names, enums as strings)."""
    data: dict[str, Any] = {SCHEMA_KEY: CURRENT_SCHEMA_VERSION}
    for section in _FLAT_SECTIONS:
        data[section] = _plain(getattr(settings, section))
    data["player"] = {
        "values": {k: _plain(v) for k, v in settings.player.values.items()},
        "ammo": {k: _plain(v) for k, v in settings.player.ammo.items()},
    }
    data["keybinds"] = {
        action_id: {"key": keys.VK_TO_NAME.get(b.key) if b.key is not None else None, "mode": b.mode.value}
        for action_id, b in settings.keybinds.binds.items()
    }
    return data


class _Invalid(Exception):
    """Internal: a value couldn't be coerced to its field type."""


def _clamp(value: float, rng: tuple[float, float] | None) -> float:
    return value if rng is None else max(rng[0], min(rng[1], value))


def _coerce(value: Any, hint: Any, name: str, rng: tuple[float, float] | None) -> Any:
    """Coerce a JSON value to the field's type hint, or raise _Invalid."""
    origin = typing.get_origin(hint)
    if origin in (UnionType, typing.Union):  # e.g. tuple[int, int] | None
        if value is None:
            return None
        inner = [a for a in typing.get_args(hint) if a is not type(None)]
        return _coerce(value, inner[0], name, rng)
    if origin is tuple:
        if not isinstance(value, (list, tuple)) or len(value) != len(typing.get_args(hint)):
            raise _Invalid(f"expected a list of {len(typing.get_args(hint))}")
        return tuple(_coerce(v, t, name, None) for v, t in zip(value, typing.get_args(hint)))
    if hint is bool:
        if not isinstance(value, bool):
            raise _Invalid("expected true/false")
        return value
    if hint in (int, float):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise _Invalid("expected a number")
        clamped = _clamp(value, rng)
        return int(round(clamped)) if hint is int else float(clamped)
    if hint is str:
        if not isinstance(value, str):
            raise _Invalid("expected a string")
        if name.endswith("colour"):
            if not _COLOUR_RE.match(value):
                raise _Invalid("expected #RRGGBB or #RRGGBBAA")
            return (value if len(value) == 9 else value + _OPAQUE_ALPHA).upper()
        return value
    if isinstance(hint, type) and issubclass(hint, Enum):
        try:
            return hint(value)
        except ValueError:
            raise _Invalid(f"expected one of {[e.value for e in hint]}") from None
    raise _Invalid(f"unsupported type {hint}")


def _load_dataclass(cls: type, data: Any, path: str, warnings: list[str],
                    range_override: tuple[float, float] | None = None, base: Any = None) -> Any:
    """Build a flat dataclass from a dict, field by field, falling back to defaults.

    Args:
        range_override: range for every numeric field without its own metadata (used for per-stat targets).
        base: instance providing defaults (else cls()).
    """
    obj = base if base is not None else cls()
    if not isinstance(data, dict):
        if data is not None:
            warnings.append(f"{path}: expected an object, using defaults")
        return obj
    hints = typing.get_type_hints(cls)
    known = {f.name for f in fields(cls)}
    for key in data.keys() - known:
        warnings.append(f"{path}.{key}: unknown setting, ignored")
    for f in fields(cls):
        if f.name not in data:
            continue
        rng = (f.metadata[RANGE_MIN], f.metadata[RANGE_MAX]) if RANGE_MIN in f.metadata else range_override
        try:
            value = _coerce(data[f.name], hints[f.name], f.name, rng)
        except _Invalid as exc:
            warnings.append(f"{path}.{f.name}: {exc}, using default")
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value != data[f.name]:
            warnings.append(f"{path}.{f.name}: {data[f.name]} adjusted to {value} (range/rounding)")
        setattr(obj, f.name, value)
    return obj


def _load_player(data: Any, warnings: list[str]) -> PlayerSettings:
    player = PlayerSettings()
    if not isinstance(data, dict):
        return player
    values = data.get("values", {})
    ammo = data.get("ammo", {})
    for stat, default in player.values.items():
        if isinstance(values, dict) and stat in values:
            player.values[stat] = _load_dataclass(ValueSetting, values[stat], f"player.values.{stat}", warnings,
                                                  range_override=config.STAT_VALUE_RANGES[stat], base=default)
    for weapon, default in player.ammo.items():
        if isinstance(ammo, dict) and weapon in ammo:
            player.ammo[weapon] = _load_dataclass(AmmoSetting, ammo[weapon], f"player.ammo.{weapon}", warnings,
                                                  base=default)
    return player


def _load_keybinds(data: Any, settings: Settings, warnings: list[str]) -> None:
    if not isinstance(data, dict):
        return
    binds = settings.keybinds.binds
    for action_id in data.keys() - binds.keys():
        warnings.append(f"keybinds.{action_id}: unknown action, ignored")
    for action_id, bind in binds.items():
        entry = data.get(action_id)
        if not isinstance(entry, dict):
            continue
        action = ACTIONS_BY_ID[action_id]
        key_name = entry.get("key")
        key = keys.vk_from_name(key_name) if isinstance(key_name, str) else None
        if key_name is not None and key is None:
            warnings.append(f"keybinds.{action_id}: unknown key {key_name!r}, unbound")
        try:
            mode = BindMode(entry.get("mode", action.default_mode.value))
        except ValueError:
            mode = action.default_mode
            warnings.append(f"keybinds.{action_id}: bad mode, using {mode.value}")
        if mode not in action.allowed_modes:
            warnings.append(f"keybinds.{action_id}: mode {mode.value} not allowed, using {action.default_mode.value}")
            mode = action.default_mode
        binds[action_id] = Bind(key, mode)


def _migrate(data: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    version = data.get(SCHEMA_KEY, 1)
    if not isinstance(version, int) or version < 1:
        warnings.append(f"{SCHEMA_KEY}: invalid ({version!r}), assuming 1")
        version = 1
    if version > CURRENT_SCHEMA_VERSION:
        warnings.append(f"profile is from a newer version ({version}); loading what we understand")
        return data
    while version < CURRENT_SCHEMA_VERSION:
        data = MIGRATIONS[version](data)
        version += 1
        log.info("migrated profile to schema %d", version)
    return data


def from_dict(data: Any) -> tuple[Settings, list[str]]:
    """JSON dict -> (Settings, warnings). Never raises on bad content."""
    warnings: list[str] = []
    settings = default_settings()
    if not isinstance(data, dict):
        return settings, ["profile is not a JSON object, using defaults"]
    data = _migrate(dict(data), warnings)
    known = {SCHEMA_KEY, *_FLAT_SECTIONS, "player", "keybinds"}
    for key in data.keys() - known:
        warnings.append(f"{key}: unknown section, ignored")
    for section in _FLAT_SECTIONS:
        current = getattr(settings, section)
        setattr(settings, section, _load_dataclass(type(current), data.get(section), section, warnings))
    settings.player = _load_player(data.get("player"), warnings)
    _load_keybinds(data.get("keybinds"), settings, warnings)
    return settings, warnings


# --- profile files --------------------------------------------------------------------

class ProfileStore:
    """Profiles stored as <directory>/<name>.json, plus a marker file for the last used profile."""

    def __init__(self, directory: Path = config.PROFILES_DIR) -> None:
        self.directory = Path(directory)
        self.last_warnings: list[str] = []

    @staticmethod
    def validate_name(name: str) -> str:
        """Return the cleaned name, or raise ProfileError if it isn't a safe file name."""
        cleaned = name.strip()
        if (not cleaned or len(cleaned) > config.PROFILE_NAME_MAX_LENGTH or not _NAME_RE.match(cleaned)
                or cleaned.lower() in _RESERVED_NAMES):
            raise ProfileError(f"invalid profile name {name!r}: use letters, digits, space, _ or - "
                               f"(max {config.PROFILE_NAME_MAX_LENGTH})")
        return cleaned

    @staticmethod
    def is_read_only(name: str) -> bool:
        """The committed default profile is never overwritten, renamed or deleted."""
        return name.strip().lower() == config.DEFAULT_PROFILE

    def path_for(self, name: str) -> Path:
        return self.directory / f"{self.validate_name(name)}{config.PROFILE_EXTENSION}"

    def list_profiles(self) -> list[str]:
        """Profile names, default first, then alphabetical."""
        if not self.directory.is_dir():
            return []
        names = [p.stem for p in self.directory.glob(f"*{config.PROFILE_EXTENSION}")
                 if _NAME_RE.match(p.stem)]
        return sorted(names, key=lambda n: (not self.is_read_only(n), n.lower()))

    def exists(self, name: str) -> bool:
        return self.path_for(name).is_file()

    def load(self, name: str) -> Settings:
        """Load a profile. Content problems become warnings (see last_warnings).

        Raises:
            ProfileError: missing file, unreadable file or invalid JSON.
        """
        path = self.path_for(name)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ProfileError(f"profile {name!r} does not exist") from None
        except (OSError, json.JSONDecodeError) as exc:
            raise ProfileError(f"could not read profile {name!r}: {exc}") from exc
        settings, self.last_warnings = from_dict(data)
        for w in self.last_warnings:
            log.warning("profile %s: %s", name, w)
        return settings

    def save(self, name: str, settings: Settings, allow_read_only: bool = False) -> None:
        """Write a profile atomically (temp file + replace, so a crash can't leave half a file).

        Raises:
            ProfileError: bad name, read-only profile, or write failure.
        """
        if self.is_read_only(name) and not allow_read_only:
            raise ProfileError(f"profile {name!r} is read-only; use Save as")
        path = self.path_for(name)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(to_dict(settings), indent=_JSON_INDENT) + "\n", encoding="utf-8")
            os.replace(tmp, path)
        except OSError as exc:
            raise ProfileError(f"could not save profile {name!r}: {exc}") from exc
        log.info("saved profile %s", name)

    def rename(self, old: str, new: str) -> None:
        """Rename a profile (and the last-used marker if it pointed at it)."""
        if self.is_read_only(old) or self.is_read_only(new):
            raise ProfileError(f"{config.DEFAULT_PROFILE!r} can't be renamed or replaced")
        src, dst = self.path_for(old), self.path_for(new)
        if not src.is_file():
            raise ProfileError(f"profile {old!r} does not exist")
        if dst.exists():
            raise ProfileError(f"profile {new!r} already exists")
        try:
            src.rename(dst)
        except OSError as exc:
            raise ProfileError(f"could not rename {old!r}: {exc}") from exc
        if self.get_last_profile() == old:
            self.set_last_profile(self.validate_name(new))

    def delete(self, name: str) -> None:
        if self.is_read_only(name):
            raise ProfileError(f"{config.DEFAULT_PROFILE!r} can't be deleted")
        path = self.path_for(name)
        try:
            path.unlink()
        except FileNotFoundError:
            raise ProfileError(f"profile {name!r} does not exist") from None
        except OSError as exc:
            raise ProfileError(f"could not delete {name!r}: {exc}") from exc

    # --- last used profile ---------------------------------------------------------

    def get_last_profile(self) -> str | None:
        try:
            name = (self.directory / config.LAST_PROFILE_FILE).read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return name or None

    def set_last_profile(self, name: str) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            (self.directory / config.LAST_PROFILE_FILE).write_text(self.validate_name(name), encoding="utf-8")
        except OSError as exc:
            log.warning("could not remember last profile: %s", exc)

    def load_startup(self) -> tuple[str, Settings]:
        """Settings to start with: the last used profile, else 'default', else built-in defaults.

        Never raises: a missing or broken profile is logged and skipped.
        """
        candidates = [n for n in (self.get_last_profile(), config.DEFAULT_PROFILE) if n]
        for name in candidates:
            try:
                return name, self.load(name)
            except ProfileError as exc:
                log.warning("startup: %s", exc)
        self.last_warnings = []
        return config.DEFAULT_PROFILE, default_settings()
