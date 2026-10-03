"""Tests for input/keybinds.py (state machine + conflicts) and input/actions.py (registry)."""

from __future__ import annotations

from actrainer import config
from actrainer.input.actions import (
    ACTIONS,
    ACTIONS_BY_ID,
    AIMBOT_ACTIVATE,
    MENU_TOGGLE,
    PANIC,
    Bind,
    BindMode,
    default_binds,
    freeze_action_id,
    set_action_id,
)
from actrainer.input.keybinds import KeybindEngine, find_conflicts
from actrainer.input.keys import VK_END, VK_INSERT, VK_RBUTTON

KEY_A, KEY_B = 0x41, 0x42


def run(engine: KeybindEngine, binds: dict[str, Bind], *frames: set[int]) -> list:
    return [engine.update(f, binds) for f in frames]


# --- modes ------------------------------------------------------------------------

def test_hold_is_active_only_while_held() -> None:
    binds = {"x": Bind(KEY_A, BindMode.HOLD)}
    states = run(KeybindEngine(), binds, set(), {KEY_A}, {KEY_A}, set())
    assert [s.is_active("x") for s in states] == [False, True, True, False]


def test_toggle_flips_on_each_press() -> None:
    binds = {"x": Bind(KEY_A, BindMode.TOGGLE)}
    frames = [{KEY_A}, {KEY_A}, set(), {KEY_A}, set(), set()]
    states = run(KeybindEngine(), binds, *frames)
    # on at first press, stays on while held, off on the second press, stays off.
    assert [s.is_active("x") for s in states] == [True, True, True, False, False, False]


def test_press_fires_once_per_press() -> None:
    binds = {"x": Bind(KEY_A, BindMode.PRESS)}
    states = run(KeybindEngine(), binds, {KEY_A}, {KEY_A}, {KEY_A}, set(), {KEY_A})
    assert [s.fired("x") for s in states] == [True, False, False, False, True]
    assert not any(s.is_active("x") for s in states)  # PRESS is never "active"


def test_unbound_action_never_triggers() -> None:
    binds = {"x": Bind(None, BindMode.HOLD)}
    (s,) = run(KeybindEngine(), binds, {KEY_A, KEY_B})
    assert not s.is_active("x") and not s.fired("x")


def test_several_actions_in_one_tick() -> None:
    binds = {"hold": Bind(KEY_A, BindMode.HOLD), "press": Bind(KEY_B, BindMode.PRESS)}
    (s,) = run(KeybindEngine(), binds, {KEY_A, KEY_B})
    assert s.is_active("hold") and s.fired("press")


def test_same_key_drives_two_actions() -> None:
    binds = {"a": Bind(KEY_A, BindMode.PRESS), "b": Bind(KEY_A, BindMode.HOLD)}
    (s,) = run(KeybindEngine(), binds, {KEY_A})
    assert s.fired("a") and s.is_active("b")


# --- suspension (menu capturing a bind) -----------------------------------------------

def test_suspended_ignores_presses_and_does_not_fire_after_resume() -> None:
    engine = KeybindEngine()
    binds = {"x": Bind(KEY_A, BindMode.PRESS)}
    assert not engine.update({KEY_A}, binds, suspended=True).fired("x")
    # Key still held after capture ends: no rising edge, so it must NOT fire now.
    assert not engine.update({KEY_A}, binds).fired("x")
    engine.update(set(), binds)
    assert engine.update({KEY_A}, binds).fired("x")


def test_suspended_keeps_toggle_state() -> None:
    engine = KeybindEngine()
    binds = {"x": Bind(KEY_A, BindMode.TOGGLE)}
    engine.update({KEY_A}, binds)
    assert engine.update(set(), binds, suspended=True).is_active("x")


def test_reset_toggles() -> None:
    engine = KeybindEngine()
    binds = {"x": Bind(KEY_A, BindMode.TOGGLE)}
    engine.update({KEY_A}, binds)
    engine.reset_toggles()
    assert not engine.update(set(), binds).is_active("x")


# --- conflicts ----------------------------------------------------------------------

def test_find_conflicts() -> None:
    binds = {"a": Bind(KEY_A), "b": Bind(KEY_A), "c": Bind(KEY_B), "d": Bind(None), "e": Bind(None)}
    assert find_conflicts(binds) == {KEY_A: ["a", "b"]}


def test_default_binds_have_no_conflicts() -> None:
    assert find_conflicts(default_binds()) == {}


# --- registry ----------------------------------------------------------------------

def test_registry_defaults() -> None:
    binds = default_binds()
    assert binds[MENU_TOGGLE] == Bind(VK_INSERT, BindMode.PRESS)
    assert binds[PANIC] == Bind(VK_END, BindMode.PRESS)
    assert binds[AIMBOT_ACTIVATE] == Bind(VK_RBUTTON, BindMode.HOLD)


def test_every_value_has_set_and_freeze_actions() -> None:
    for value_id in (*config.STAT_VALUES, *config.WEAPONS):
        assert set_action_id(value_id) in ACTIONS_BY_ID
        assert freeze_action_id(value_id) in ACTIONS_BY_ID


def test_action_ids_unique_and_default_mode_allowed() -> None:
    assert len(ACTIONS_BY_ID) == len(ACTIONS)
    for a in ACTIONS:
        assert a.default_mode in a.allowed_modes, a.id


def test_default_binds_returns_fresh_objects() -> None:
    a, b = default_binds(), default_binds()
    a[MENU_TOGGLE].key = None
    assert b[MENU_TOGGLE].key == VK_INSERT
