"""Tests for ui/profile_session.py: dirty flag and profile actions on the shared Settings object."""

from __future__ import annotations

import pytest

from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.settings.store import ProfileError, default_settings
from actrainer.ui.profile_session import ProfileSession


def test_any_change_marks_dirty(session: ProfileSession, signals: AppSignals) -> None:
    assert not session.dirty
    signals.settings_changed.emit("aimbot")
    assert session.dirty


def test_save_on_read_only_default_raises(session: ProfileSession) -> None:
    assert session.read_only
    with pytest.raises(ProfileError):
        session.save()


def test_save_as_then_save_clears_dirty(session: ProfileSession, settings: Settings, signals: AppSignals) -> None:
    settings.aimbot.fov_deg = 33.0
    signals.settings_changed.emit("aimbot")
    session.save_as("mine")
    assert session.current == "mine" and not session.dirty and not session.read_only
    assert session.store.load("mine").aimbot.fov_deg == 33.0
    assert session.store.get_last_profile() == "mine"
    signals.settings_changed.emit("aimbot")
    session.save()
    assert not session.dirty


def test_load_replaces_settings_in_place_and_requests_refresh(session: ProfileSession, settings: Settings,
                                                              signals: AppSignals) -> None:
    other = default_settings()
    other.esp.enabled = True
    session.store.save("other", other)
    refreshed: list[bool] = []
    signals.refresh_requested.connect(lambda: refreshed.append(True))
    shared = settings  # the object everyone holds
    session.load("other")
    assert shared.esp.enabled is True
    assert refreshed and session.current == "other" and not session.dirty


def test_load_keeps_menu_position(session: ProfileSession, settings: Settings) -> None:
    settings.general.menu_pos = (300, 200)
    other = default_settings()
    other.general.menu_pos = (5, 5)
    session.store.save("other", other)
    session.load("other")
    assert settings.general.menu_pos == (300, 200)


def test_reset_to_defaults_marks_dirty(session: ProfileSession, settings: Settings) -> None:
    settings.aimbot.enabled = True
    session.reset_to_defaults()
    assert settings.aimbot.enabled is False and session.dirty


def test_rename_current_follows(session: ProfileSession) -> None:
    session.save_as("a")
    session.rename("a", "b")
    assert session.current == "b"
    assert "b" in session.profiles()
