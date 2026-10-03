"""Tests for main.py helpers: single-instance lock and the exception hook."""

from __future__ import annotations

import logging

import pytest

from actrainer import config, main


def test_second_instance_lock_fails(monkeypatch: pytest.MonkeyPatch, qapp) -> None:  # noqa: ANN001
    monkeypatch.setattr(config, "LOCK_FILE_NAME", "actrainer-test.lock")
    first = main.acquire_single_instance_lock()
    assert first is not None
    try:
        assert main.acquire_single_instance_lock() is None
    finally:
        first.unlock()
    again = main.acquire_single_instance_lock()
    assert again is not None
    again.unlock()


def test_unhandled_exceptions_are_logged_not_fatal(caplog: pytest.LogCaptureFixture) -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        with caplog.at_level(logging.CRITICAL):
            main.log_unhandled(type(exc), exc, exc.__traceback__)
    assert "unhandled exception" in caplog.text and "boom" in caplog.text
