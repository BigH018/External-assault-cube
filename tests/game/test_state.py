"""Tests for game/state.py and local_player.write_view_angles (fake process)."""

from __future__ import annotations

import struct

import pytest

from actrainer import offsets
from actrainer.game.local_player import write_view_angles
from actrainer.game.player import read_player
from actrainer.game.state import read_game_state
from actrainer.maths.angles import Angles
from helpers.fake_game import make_fake_game


def test_reads_local_and_live_bots() -> None:
    proc, local, _ = make_fake_game(bots=[{"name": b"Alpha"}, {"name": b"Ghost", "dead": 1, "health": -20},
                                          {"name": b"Bravo"}])
    state = read_game_state(proc)
    assert state is not None
    assert state.local.address == local
    assert [b.name for b in state.entities] == ["Alpha", "Bravo"]  # dead excluded


def test_no_local_player_gives_none() -> None:
    proc, _, _ = make_fake_game(bots=[{"name": b"Alpha"}])
    proc.put_u32(proc.module_base + offsets.LOCAL_PLAYER_PTR, 0)
    assert read_game_state(proc) is None


def test_write_view_angles_is_one_8_byte_write() -> None:
    proc, local, _ = make_fake_game()
    write_view_angles(proc, local, Angles(123.5, -12.25))
    assert proc.writes == [(local + offsets.VIEW_YAW, struct.pack("<2f", 123.5, -12.25))]
    me = read_player(proc, local)
    assert (me.yaw, me.pitch) == pytest.approx((123.5, -12.25))
