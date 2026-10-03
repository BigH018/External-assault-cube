"""Tests for game/entities.py using a fake process (no game needed)."""

from __future__ import annotations

import struct

from actrainer import config, offsets
from actrainer.game.entities import read_entities, read_entity_pointers, read_player_count
from helpers.fake_game import FakeProcess, make_player_buffer

LIST_ADDRESS = 0x00A58AE8
LOCAL = 0x009DD2C8
BOT_A = 0x18994B58
BOT_B = 0x189931A8
BOT_DEAD = 0x18995830
BOT_GARBAGE = 0x189935F0
BOT_UNREADABLE = 0x189924D0


def make_game(slots: list[int], count: int | None = None) -> FakeProcess:
    """Fake process with an entity list holding `slots` and the matching player structs."""
    proc = FakeProcess()
    proc.put_u32(proc.module_base + offsets.ENTITY_LIST_PTR, LIST_ADDRESS)
    proc.put_i32(proc.module_base + offsets.PLAYER_COUNT, len(slots) if count is None else count)
    proc.put(LIST_ADDRESS, struct.pack(f"<{len(slots)}I", *slots))
    proc.put(LOCAL, make_player_buffer(name=b"me"))
    proc.put(BOT_A, make_player_buffer(name=b"Alpha", health=80))
    proc.put(BOT_B, make_player_buffer(name=b"Bravo", health=35, team=1))
    proc.put(BOT_DEAD, make_player_buffer(name=b"Dead", health=-54, dead=1))
    proc.put(BOT_GARBAGE, make_player_buffer(name=b"Junk", feet=(1e30, 0.0, 0.0)))
    # BOT_UNREADABLE is deliberately not mapped: reading it raises MemoryAccessError.
    return proc


def names(players: list) -> list[str]:
    return [p.name for p in players]


def test_reads_bots_and_skips_null_and_local() -> None:
    proc = make_game([0, LOCAL, BOT_A, BOT_B])
    assert names(read_entities(proc, local_address=LOCAL)) == ["Alpha", "Bravo"]


def test_skips_dead_by_default_but_can_include_them() -> None:
    proc = make_game([0, BOT_A, BOT_DEAD])
    assert names(read_entities(proc, LOCAL)) == ["Alpha"]
    assert names(read_entities(proc, LOCAL, include_dead=True)) == ["Alpha", "Dead"]


def test_skips_garbage_and_unreadable_entities_without_crashing() -> None:
    proc = make_game([0, BOT_GARBAGE, BOT_UNREADABLE, 0x1234, BOT_B])
    assert names(read_entities(proc, LOCAL)) == ["Bravo"]


def test_bad_player_count_gives_empty_list() -> None:
    assert read_entities(make_game([0, BOT_A], count=-1), LOCAL) == []
    assert read_player_count(make_game([0, BOT_A], count=config.MAX_ENTITIES + 1)) == 0


def test_null_list_pointer_gives_empty_list() -> None:
    proc = make_game([0, BOT_A])
    proc.put_u32(proc.module_base + offsets.ENTITY_LIST_PTR, 0)
    assert read_entity_pointers(proc) == []


def test_entity_pointers_are_read_as_uint32() -> None:
    # 0x80000000+ would be negative if mistakenly read as signed; must stay a large unsigned int.
    proc = make_game([0, 0x80000010])
    assert read_entity_pointers(proc) == [0, 0x80000010]
