"""Attach to ac_client.exe and read/write its memory with typed helpers.

This is the only module that imports pymem. Everything above it works with plain ints, floats
and bytes, and with the two exceptions defined here, so the rest of the code never needs to know
pymem exists.

Why we unpack bytes ourselves instead of using pymem.read_int etc.:
- We decide the exact size and format of every value. That matters because ac_client.exe is a
  **32-bit** process: a pointer there is 4 bytes, even though our Python is 64-bit.
- `struct` format codes make the layout explicit: "<" = little-endian (x86), "I" = uint32,
  "i" = int32, "f" = float32.
"""

from __future__ import annotations

import logging
import struct
from types import TracebackType

import pymem
import pymem.exception
import pymem.process

from actrainer import config

log = logging.getLogger(__name__)
# pymem installs its own DEBUG-level handler on import, which spams our console. Keep only its warnings.
logging.getLogger("pymem").setLevel(logging.WARNING)

# Every error pymem can raise during attach/read/write. WinAPIError does not inherit PymemError.
_PYMEM_ERRORS = (pymem.exception.PymemError, pymem.exception.WinAPIError)

_U32 = struct.Struct("<I")
_I32 = struct.Struct("<i")
_F32 = struct.Struct("<f")

# Every Windows executable starts with the "MZ" DOS header. If we can still read it at the
# module base, the process is alive and our handle still works.
_PE_MAGIC = b"MZ"


class AttachError(Exception):
    """The game process could not be found or opened."""


class MemoryAccessError(Exception):
    """A read or write into the game process failed (bad address, or the process went away)."""


class GameProcess:
    """A handle to the running game, with typed memory helpers.

    Usage:
        proc = GameProcess()
        proc.attach()            # raises AttachError if the game isn't running
        hp = proc.read_i32(addr)
    """

    def __init__(self, process_name: str = config.PROCESS_NAME) -> None:
        self._process_name = process_name
        self._pm: pymem.Pymem | None = None
        self._module_base: int = 0

    # --- lifecycle -------------------------------------------------------------

    def attach(self) -> None:
        """Open the game process and find the base address of its main module.

        Raises:
            AttachError: if the process isn't running or can't be opened
                (e.g. the game runs as admin and we don't).
        """
        self.detach()
        try:
            pm = pymem.Pymem(self._process_name)
            module = pymem.process.module_from_name(pm.process_handle, self._process_name)
        except _PYMEM_ERRORS as exc:
            raise AttachError(f"could not attach to {self._process_name}: {exc}") from exc
        if module is None:
            pm.close_process()
            raise AttachError(f"module {self._process_name} not found in process")

        self._pm = pm
        # lpBaseOfDll = where Windows loaded the exe in the game's address space.
        # All static offsets in offsets.py are relative to this.
        self._module_base = module.lpBaseOfDll
        log.info("attached to %s (pid %d), module base 0x%08X",
                 self._process_name, pm.process_id, self._module_base)

    def detach(self) -> None:
        """Close the process handle. Safe to call when not attached."""
        if self._pm is not None:
            try:
                self._pm.close_process()
            except _PYMEM_ERRORS:
                pass  # the process may already be gone; nothing useful to do
            log.info("detached from %s", self._process_name)
        self._pm = None
        self._module_base = 0

    @property
    def is_attached(self) -> bool:
        """True if we hold an open handle (the process may still have exited since)."""
        return self._pm is not None

    def is_alive(self) -> bool:
        """True if attached AND the process still answers reads."""
        if self._pm is None:
            return False
        try:
            return self._pm.read_bytes(self._module_base, len(_PE_MAGIC)) == _PE_MAGIC
        except _PYMEM_ERRORS:
            return False

    @property
    def module_base(self) -> int:
        """Base address of ac_client.exe in the game's memory (0 if not attached)."""
        return self._module_base

    @property
    def pid(self) -> int:
        """Process id of the game (0 if not attached)."""
        return self._pm.process_id if self._pm is not None else 0

    def __enter__(self) -> GameProcess:
        self.attach()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 tb: TracebackType | None) -> None:
        self.detach()

    # --- reads -------------------------------------------------------------------

    def read_bytes(self, address: int, size: int) -> bytes:
        """Read `size` raw bytes at `address`.

        Raises:
            MemoryAccessError: if not attached or the read fails.
        """
        if self._pm is None:
            raise MemoryAccessError("not attached")
        try:
            return self._pm.read_bytes(address, size)
        except _PYMEM_ERRORS as exc:
            raise MemoryAccessError(f"read of {size} bytes at 0x{address:08X} failed: {exc}") from exc

    def read_u32(self, address: int) -> int:
        """Read an unsigned 32-bit int. Use this for POINTERS in the 32-bit game."""
        return _U32.unpack(self.read_bytes(address, _U32.size))[0]

    def read_i32(self, address: int) -> int:
        """Read a signed 32-bit int (health, ammo, team, ...)."""
        return _I32.unpack(self.read_bytes(address, _I32.size))[0]

    def read_f32(self, address: int) -> float:
        """Read a 32-bit float (angles, FOV, ...)."""
        return _F32.unpack(self.read_bytes(address, _F32.size))[0]

    def read_f32_array(self, address: int, count: int) -> tuple[float, ...]:
        """Read `count` consecutive 32-bit floats in one call (e.g. the 16-float view matrix)."""
        return struct.unpack(f"<{count}f", self.read_bytes(address, count * _F32.size))

    # --- writes ------------------------------------------------------------------

    def write_bytes(self, address: int, data: bytes) -> None:
        """Write raw bytes at `address`.

        Raises:
            MemoryAccessError: if not attached or the write fails.
        """
        if self._pm is None:
            raise MemoryAccessError("not attached")
        try:
            self._pm.write_bytes(address, data, len(data))
        except _PYMEM_ERRORS as exc:
            raise MemoryAccessError(f"write of {len(data)} bytes at 0x{address:08X} failed: {exc}") from exc

    def write_i32(self, address: int, value: int) -> None:
        """Write a signed 32-bit int."""
        self.write_bytes(address, _I32.pack(value))

    def write_f32(self, address: int, value: float) -> None:
        """Write a 32-bit float."""
        self.write_bytes(address, _F32.pack(value))
