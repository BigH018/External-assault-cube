"""Project-wide constants that are NOT memory offsets.

Offsets live in `offsets.py`. Everything else that would otherwise be a magic number lives here.
This module is pure: no I/O, no third-party imports.
"""

from __future__ import annotations

from pathlib import Path

# --- Paths -------------------------------------------------------------------
# src/actrainer/config.py -> parents[2] is the project root (works with the editable install).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_DIR = PROJECT_ROOT / "profiles"
PROFILE_EXTENSION = ".json"
LAST_PROFILE_FILE = ".last_profile"   # inside PROFILES_DIR, git-ignored
DEFAULT_PROFILE = "default"           # committed and read-only (overwrite with "Save as")
PROFILE_NAME_MAX_LENGTH = 40
LOGS_DIR = PROJECT_ROOT / "logs"      # git-ignored
LOG_FILE = "actrainer.log"
LOCK_FILE_NAME = "actrainer.lock"     # in the system temp dir; stops two trainers fighting over the game
LOCK_TIMEOUT_MS = 100

# --- Controller timing --------------------------------------------------------
ATTACH_RETRY_S = 1.0         # how often to try attaching while the game isn't found
LIVENESS_CHECK_S = 1.0       # how often to check the attached game is still alive
STATUS_INTERVAL_S = 0.5      # how often the menu's status panel is refreshed
TICK_RATE_SMOOTHING = 0.1    # weight of the newest sample in the measured tick rate (exponential average)

# --- Menu window --------------------------------------------------------------
APP_NAME = "External Cheat"
APP_AUTHOR = "By BigH"
MENU_TITLE = f"{APP_NAME} - {APP_AUTHOR}"   # window title
APP_USER_MODEL_ID = "BigH.ExternalCheat"    # lets Windows show our logo in the taskbar instead of Python's
MENU_SIZE = (920, 760)       # initial width, height in pixels
SIDEBAR_WIDTH = 190
LOGO_SIZE = 40               # header logo, pixels

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

# --- Editable player values ----------------------------------------------------
# Single-int values and weapons (each weapon has magazine + reserve ammo).
# WEAPONS must match the keys of offsets.MAG_AMMO / offsets.RESERVE_AMMO (checked by a test).
STAT_VALUES = ("health", "armor", "grenades", "akimbo")
WEAPONS = ("pistol", "carbine", "shotgun", "smg", "sniper", "assault")
# Display names, shared by the Player tab and the keybind action labels so they always match.
VALUE_NAMES = {
    "health": "Health", "armor": "Armour", "grenades": "Grenades", "akimbo": "Akimbo ammo",
    "pistol": "Pistol", "carbine": "Carbine", "shotgun": "Shotgun", "smg": "SMG",
    "sniper": "Sniper", "assault": "Assault rifle",
}

# --- Setting ranges (min, max) --------------------------------------------------
# Used by settings/models.py field metadata. That makes them the single source for store clamping AND UI slider limits.
TICK_RATE_RANGE = (10, 240)            # Hz
OVERLAY_FPS_RANGE = (10, 240)          # frames per second
AIM_FOV_RANGE = (1.0, 180.0)           # degrees from the crosshair
AIM_SMOOTHING_RANGE = (1.0, 30.0)      # 1 = instant snap
AIM_MAX_DISTANCE_RANGE = (10.0, 2000.0)  # world units (player eye height is about 4.5 units)
LINE_THICKNESS_RANGE = (1, 10)         # pixels
# Game FOV (written to offsets.VIEW_FOV). Verified 2026-10-03: the game renders any written value (30..170 tested)
# without clamping. Above ~150 the image distorts badly, and 180 breaks the projection maths.
GAME_FOV_RANGE = (30.0, 150.0)         # degrees, horizontal
GAME_FOV_EPSILON = 0.01                # smaller differences count as "already applied"

# Value caps for the Player tab: no negatives, sensible maximums.
STAT_VALUE_RANGES = {
    "health": (1, 999),
    "armor": (0, 999),
    "grenades": (0, 99),
    "akimbo": (0, 999),
}
MAG_AMMO_RANGE = (0, 999)
RESERVE_AMMO_RANGE = (0, 999)
