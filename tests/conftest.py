"""Shared fixtures. Qt runs on the offscreen platform, so no windows appear during tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication  # noqa: E402

from actrainer.settings.models import Settings  # noqa: E402
from actrainer.settings.signals import AppSignals  # noqa: E402
from actrainer.settings.store import ProfileStore, default_settings  # noqa: E402
from actrainer.ui.profile_session import ProfileSession  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def settings() -> Settings:
    return default_settings()


@pytest.fixture
def signals(qapp: QApplication) -> AppSignals:
    return AppSignals()


@pytest.fixture
def store(tmp_path: Path) -> ProfileStore:
    s = ProfileStore(tmp_path / "profiles")
    s.save("default", default_settings(), allow_read_only=True)
    return s


@pytest.fixture
def session(store: ProfileStore, settings: Settings, signals: AppSignals) -> ProfileSession:
    return ProfileSession(store, settings, signals, "default")
