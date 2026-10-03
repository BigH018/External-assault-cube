"""ALL memory offsets for AssaultCube. This is the single source of truth.

Changing a value requires following the Offset change rule (CLAUDE.md §6): prove it, keep the old
value in a comment, log it, and flag "OFFSET CHANGED". Never change an offset on a guess.
Pure module: constants only.
"""

from __future__ import annotations

GAME_VERSION = "1.3.0.2"
MODULE_NAME = "ac_client.exe"

# --- Static offsets (relative to ac_client.exe module base) -------------------

# These three sit together because the game declares them together:
#   playerent *player1;  vector<playerent*> players { buf, alen (capacity), ulen (count) };
LOCAL_PLAYER_PTR = 0x18AC00  # pointer: `player1`, the local player. Stays valid while dead. (was 0x17E0A8 = camera1)
ENTITY_LIST_PTR = 0x18AC04   # pointer: to an array of uint32 entity pointers (players.buf)
PLAYER_COUNT = 0x18AC0C      # int: number of players, INCLUDING the local player (players.ulen)

# `camera1`: what the camera follows. Equals player1 while alive, but switches to a separate
# death-cam object when you die. Was wrongly used as the local player pointer before 2026-10-03.
# Don't read player fields through it.
CAMERA_PTR = 0x17E0A8
VIEW_FOV = 0x18A7CC          # float: current field of view in degrees
VIEW_MATRIX = 0x17DFD0       # 16 floats stored IN PLACE (not a pointer), OpenGL column-major

POINTER_SIZE = 4             # 32-bit process: every pointer is 4 bytes

# --- Player / entity struct offsets (relative to the player address) ----------

HEAD_POS = 0x04              # Vec3 (3 floats), z is up
FEET_POS = 0x28              # Vec3 (3 floats)
VIEW_YAW = 0x34              # float, 0..360 degrees
VIEW_PITCH = 0x38            # float, -90..90 degrees
HEALTH = 0xEC                # int
ARMOR = 0xF0                 # int

RESERVE_AMMO = {             # int each
    "pistol": 0x108,
    "carbine": 0x10C,
    "shotgun": 0x110,
    "smg": 0x114,
    "sniper": 0x118,
    "assault": 0x11C,
}
MAG_AMMO = {                 # int each
    "pistol": 0x12C,
    "carbine": 0x130,
    "shotgun": 0x134,
    "smg": 0x138,
    "sniper": 0x13C,
    "assault": 0x140,
}
GRENADES = 0x144             # int
AKIMBO_AMMO = 0x148          # int
NAME = 0x205                 # char[16], null-terminated
NAME_LENGTH = 16
TEAM = 0x30C                 # int
DEAD = 0x318                 # int (non-zero = dead)

# How many bytes to read in ONE call to cover every field above (the last field, DEAD, is a 4-byte int).
# Reading the whole struct at once is far cheaper than ~20 separate cross-process reads.
PLAYER_READ_SIZE = DEAD + 4
