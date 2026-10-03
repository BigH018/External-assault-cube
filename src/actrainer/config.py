"""Project-wide constants that are NOT memory offsets.

Offsets live in `offsets.py`. Everything else that would otherwise be a magic number lives here.
This module is pure: no I/O, no third-party imports.
"""

from __future__ import annotations

# --- Process -----------------------------------------------------------------

PROCESS_NAME = "ac_client.exe"

# --- Pointer sanity ----------------------------------------------------------
# ac_client.exe is a 32-bit process, so every valid pointer fits in 32 bits.
# Addresses below 64 KiB are never valid user-space allocations on Windows, so a pointer
# in that range is null-ish garbage (e.g. a half-initialised entity slot).
MIN_VALID_POINTER = 0x0001_0000
MAX_VALID_POINTER = 0x7FFF_FFFF  # top of 32-bit user space (without /LARGEADDRESSAWARE)

# --- World sanity ------------------------------------------------------------
# AssaultCube maps are at most a few thousand units across. Anything beyond this means
# we read garbage memory, not a real position.
WORLD_COORD_LIMIT = 10_000.0

# Local player health: deliberately very wide. The trainer itself can set health to
# e.g. 999, so health must never decide whether the local player is "valid".
LOCAL_HEALTH_SANE_MIN = -1_000
LOCAL_HEALTH_SANE_MAX = 1_000_000

# Bots: a loose filter to reject garbage entity entries. Bots never get trainer edits.
# Alive bots must be in 0..100. Health goes NEGATIVE on death (-54 observed), so dead bots
# get a wider lower bound instead.
BOT_HEALTH_MIN = 0
BOT_HEALTH_MAX = 100
BOT_DEAD_HEALTH_MIN = -1_000

# The game's player vector never holds more than a few dozen entries. A bigger count means a bad read.
MAX_ENTITIES = 64

# --- Strings -----------------------------------------------------------------

NAME_ENCODING = "latin-1"  # AC names are plain single-byte chars; latin-1 never fails to decode
