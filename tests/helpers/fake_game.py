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
    """Duck-typed stand-in for GameProcess backed by writable {address: bytearray} regions.

    Behaves like an attached, alive process by default (attach/detach/is_alive/pid), so it can also
    drive the controller in tests.
    """

    def __init__(self, module_base: int = 0x00400000) -> None:
        self.module_base = module_base
        self.regions: dict[int, bytearray] = {}
        self.is_attached = True
        self.pid = 4242
        self.writes: list[tuple[int, bytes]] = []

    # --- lifecycle (GameProcess API) ---
    def attach(self) -> None:
        self.is_attached = True

    def detach(self) -> None:
        self.is_attached = False

    def is_alive(self) -> bool:
        return self.is_attached

    # --- memory ---
    def put(self, address: int, data: bytes) -> None:
        self.regions[address] = bytearray(data)

    def put_u32(self, address: int, value: int) -> None:
        self.put(address, struct.pack("<I", value))

    def put_i32(self, address: int, value: int) -> None:
        self.put(address, struct.pack("<i", value))

    def _locate(self, address: int, size: int) -> tuple[bytearray, int]:
        for start, data in self.regions.items():
            if start <= address and address + size <= start + len(data):
                return data, address - start
        raise MemoryAccessError(f"unmapped access at 0x{address:08X}")

    def read_bytes(self, address: int, size: int) -> bytes:
        data, off = self._locate(address, size)
        return bytes(data[off:off + size])

    def read_u32(self, address: int) -> int:
        return struct.unpack("<I", self.read_bytes(address, 4))[0]

    def read_i32(self, address: int) -> int:
        return struct.unpack("<i", self.read_bytes(address, 4))[0]

    def read_f32(self, address: int) -> float:
        return struct.unpack("<f", self.read_bytes(address, 4))[0]

    def read_f32_array(self, address: int, count: int) -> tuple[float, ...]:
        return struct.unpack(f"<{count}f", self.read_bytes(address, count * 4))

    def write_bytes(self, address: int, payload: bytes) -> None:
        data, off = self._locate(address, len(payload))
        data[off:off + len(payload)] = payload
        self.writes.append((address, bytes(payload)))

    def write_i32(self, address: int, value: int) -> None:
        self.write_bytes(address, struct.pack("<i", value))

    def write_f32(self, address: int, value: float) -> None:
        self.write_bytes(address, struct.pack("<f", value))


IDENTITY_MATRIX = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)
DEFAULT_FOV = 90.0


def make_fake_game(local: dict[str, object] | None = None,
                   bots: list[dict[str, object]] | None = None,
                   matrix: tuple[float, ...] = IDENTITY_MATRIX,
                   fov: float = DEFAULT_FOV) -> tuple[FakeProcess, int, list[int]]:
    """A fake process with a local player and bots wired up exactly like the real memory layout.

    Returns (process, local_address, bot_addresses).
    """
    proc = FakeProcess()
    local_addr = 0x009DD2C8
    list_addr = 0x00A58AE8
    bot_addrs = [0x18990000 + i * 0x1000 for i in range(len(bots or []))]
    proc.put_u32(proc.module_base + offsets.LOCAL_PLAYER_PTR, local_addr)
    proc.put_u32(proc.module_base + offsets.ENTITY_LIST_PTR, list_addr)
    proc.put_i32(proc.module_base + offsets.PLAYER_COUNT, len(bot_addrs) + 1)
    proc.put(list_addr, struct.pack(f"<{len(bot_addrs) + 1}I", 0, *bot_addrs))
    proc.put(local_addr, make_player_buffer(**{"name": b"me", "team": 0, **(local or {})}))
    for addr, bot in zip(bot_addrs, bots or []):
        proc.put(addr, make_player_buffer(**bot))
    proc.put(proc.module_base + offsets.VIEW_MATRIX, struct.pack("<16f", *matrix))
    proc.put(proc.module_base + offsets.VIEW_FOV, struct.pack("<f", fov))
    return proc, local_addr, bot_addrs
