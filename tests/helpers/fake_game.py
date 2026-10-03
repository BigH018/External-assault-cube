"""Fake game memory for tests: build player structs and a fake process without running the game."""

from __future__ import annotations

import struct

from actrainer import offsets
from actrainer.memory.process import MemoryAccessError

DEFAULT_PLAYER: dict[str, object] = {
    "head": (10.0, 20.0, 5.5), "feet": (10.0, 20.0, 1.0), "yaw": 90.0, "pitch": -10.0,
    "health": 100, "armor": 50, "team": 1, "dead": 0, "name": b"Harry", "grenades": 3,
    "akimbo": 0,
}


def make_player_buffer(**overrides: object) -> bytes:
    """Build a fake player struct (PLAYER_READ_SIZE bytes) with sensible values plus overrides.

    Mag ammo is 10, 11, 12... and reserve ammo is 100, 101, 102... in offsets.MAG_AMMO / RESERVE_AMMO order.
    """
    v = {**DEFAULT_PLAYER, **overrides}
    buf = bytearray(offsets.PLAYER_READ_SIZE)
    struct.pack_into("<3f", buf, offsets.HEAD_POS, *v["head"])
    struct.pack_into("<3f", buf, offsets.FEET_POS, *v["feet"])
    struct.pack_into("<f", buf, offsets.VIEW_YAW, v["yaw"])
    struct.pack_into("<f", buf, offsets.VIEW_PITCH, v["pitch"])
    for key, off in (("health", offsets.HEALTH), ("armor", offsets.ARMOR), ("team", offsets.TEAM),
                     ("dead", offsets.DEAD), ("grenades", offsets.GRENADES), ("akimbo", offsets.AKIMBO_AMMO)):
        struct.pack_into("<i", buf, off, v[key])
    for i, off in enumerate(offsets.MAG_AMMO.values()):
        struct.pack_into("<i", buf, off, 10 + i)
    for i, off in enumerate(offsets.RESERVE_AMMO.values()):
        struct.pack_into("<i", buf, off, 100 + i)
    name: bytes = v["name"]  # type: ignore[assignment]
    buf[offsets.NAME:offsets.NAME + len(name)] = name
    return bytes(buf)


class FakeProcess:
    """Duck-typed stand-in for GameProcess backed by a dict of {address: bytes} regions."""

    def __init__(self, module_base: int = 0x00400000) -> None:
        self.module_base = module_base
        self.regions: dict[int, bytes] = {}

    def put(self, address: int, data: bytes) -> None:
        self.regions[address] = data

    def put_u32(self, address: int, value: int) -> None:
        self.put(address, struct.pack("<I", value))

    def put_i32(self, address: int, value: int) -> None:
        self.put(address, struct.pack("<i", value))

    def read_bytes(self, address: int, size: int) -> bytes:
        for start, data in self.regions.items():
            if start <= address and address + size <= start + len(data):
                return data[address - start:address - start + size]
        raise MemoryAccessError(f"unmapped read at 0x{address:08X}")

    def read_u32(self, address: int) -> int:
        return struct.unpack("<I", self.read_bytes(address, 4))[0]

    def read_i32(self, address: int) -> int:
        return struct.unpack("<i", self.read_bytes(address, 4))[0]
