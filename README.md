<p align="center">
  <img src="docs/assets/logo.png" width="180" alt="External Cheat logo">
</p>

<h1 align="center">External Cheat</h1>

<p align="center">
  <b>By BigH</b><br>
  External trainer for AssaultCube 1.3.0.2, written in Python<br>
  <sub>Personal learning project · offline bot matches only</sub>
</p>

---

A personal learning project: an **external** trainer for **AssaultCube 1.3.0.2**, written in Python. It's a normal,
separate program that sits *next to* the game. It never puts any code inside the game. Everything happens from the outside:
it reads and writes the game's memory with `ReadProcessMemory` / `WriteProcessMemory`, works out where every bot is,
does the vector maths for an aimbot, and draws an ESP on a transparent window laid over the game. A PyQt5 menu
controls it all.

It covers process memory, pointer chains, struct layouts, finding offsets yourself, aim-angle maths, world-to-screen
projection, a click-through overlay, global hotkeys and building a real desktop app with profiles. The
[How it works](#how-it-works-the-educational-part) section explains each of those step by step, with the real addresses
and numbers from the game.

The follow-up project is [**Internal Cheat**](https://github.com/BigH018/internal-assault-cube), a C++ DLL that does the
same things from *inside* the game, plus features only an internal trainer can do. Read this one first: the internal
README builds on the basics explained here.

> **Scope:** offline, single-player bot matches on my own PC only. AssaultCube 1.3.0.2 has no anti-cheat, and this
> project never tries to hide from one. No multiplayer or online use, no anti-cheat bypass or evasion, no injection or
> DLLs, no network code, no distribution. It's a plain Python program that opens the game's process the documented way.

## Screenshots

<p align="center">
  <img src="docs/screenshots/esp.jpg" width="100%" alt="ESP in-game: boxes, head circles, names, health bars, distance and the FOV circle">
  <br><sub><b>In-game:</b> 2D boxes, head circles, names, health bars, distance and the aimbot FOV circle (bots seen through walls)</sub>
</p>

<p align="center">
  <img src="docs/screenshots/esp-skeleton.jpg" width="100%" alt="ESP in-game: corner boxes, skeletons and health numbers">
  <br><sub><b>In-game:</b> corner boxes, approximate skeletons and health numbers in a custom colour</sub>
</p>

<table>
  <tr>
    <td align="center" width="50%"><img src="docs/screenshots/menu-aimbot.png" alt="Aimbot page"><br><sub><b>Aimbot</b>: key and mode, targeting, FOV, smoothing</sub></td>
    <td align="center" width="50%"><img src="docs/screenshots/menu-esp.png" alt="ESP page"><br><sub><b>ESP</b>: styles, colours and info</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/screenshots/menu-player.png" alt="Player page"><br><sub><b>Player</b>: game FOV, set/freeze values with live readouts</sub></td>
    <td align="center"><img src="docs/screenshots/colour-picker.png" alt="Colour picker"><br><sub><b>Colour picker</b>: presets, custom colour, opacity, live preview</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/screenshots/menu-keybinds.png" alt="Keybinds page"><br><sub><b>Keybinds</b>: every action, any key or mouse button</sub></td>
    <td align="center"><img src="docs/screenshots/menu-settings.png" alt="Settings page"><br><sub><b>Settings</b>: profiles, performance, live status</sub></td>
  </tr>
</table>

<sub>The ESP images are the live game's window with the overlay's own drawing code applied (the same painter the overlay
uses). The menu pages are rendered offscreen with live status from the running game. Regenerate them with
<code>tools\readme_shots_game.py</code> and <code>tools\readme_shots_menu.py</code>.</sub>

## Contents
- [Screenshots](#screenshots)
- [Features](#features)
- [Requirements](#requirements) · [Install](#install) · [Run](#run) · [Using the menu](#using-the-menu) ·
  [Troubleshooting](#troubleshooting) · [Debug tools](#debug-tools) · [Tests](#tests) · [Project layout](#project-layout)
- [How it works (the educational part)](#how-it-works-the-educational-part)
  1. [External vs internal](#1-external-vs-internal-what-a-separate-process-can-do)
  2. [Attaching to the game](#2-attaching-to-the-game)
  3. [Bytes, pointers and 32-bit](#3-bytes-pointers-and-32-bit)
  4. [Pointer chains and the player struct](#4-pointer-chains-and-the-player-struct)
  5. [The entity list](#5-the-entity-list-finding-every-bot)
  6. [Finding offsets: a real bug](#6-finding-offsets-a-real-bug-from-this-project)
  7. [Aim angles](#7-aim-angles-assaultcubes-yaw-convention)
  8. [The aimbot](#8-the-aimbot-filter-prioritise-smooth-write)
  9. [World-to-screen](#9-world-to-screen-the-view-matrix)
  10. [The ESP](#10-the-esp-boxes-skeletons-and-the-fov-circle)
  11. [The overlay window](#11-the-overlay-window)
  12. [Player values, freezes and the game FOV](#12-player-values-freezes-and-the-game-fov)
  13. [Global hotkeys and the keybind engine](#13-global-hotkeys-and-the-keybind-engine)
  14. [A menu over a game that grabs the mouse](#14-a-menu-over-a-game-that-grabs-the-mouse)
  15. [Settings and profiles](#15-settings-and-profiles)
  16. [Never crash](#16-never-crash-errors-reattach-and-one-instance)
  17. [Testing without the game](#17-testing-without-the-game)
  18. [How it all fits together](#18-how-it-all-fits-together)
  19. [What I learned, phase by phase](#19-what-i-learned-phase-by-phase)
- [Credits and licences](#credits-and-licences)

## Features
- **Menu:** dark PyQt5 window with sidebar navigation, toggle switches and an ice-blue accent, toggled with **INSERT**
  (even from inside the game). Every change applies live. Profiles use explicit Save.
- **Aimbot:** hold/toggle key (default: hold right mouse), head/body, priority (crosshair / distance / lowest health),
  FOV radius + circle, smoothing, team check, max distance. Only aims while the game window is focused.
- **ESP overlay:** 2D box, corner box, head circle and approximate skeleton (combinable); name, health bar, health number,
  distance, snaplines; team mode and enemies only; colours (picker with presets, custom colour, opacity, live preview)
  and line thickness. Transparent and click-through.
- **Player values:** health, armour, grenades, akimbo, and magazine/reserve ammo per weapon. Each has Set now, Freeze
  and optional hotkeys, plus a live readout of the in-game value.
- **Game FOV:** change the game's own field of view (30–150°), set once or keep applied. Your original FOV comes back on
  panic and quit.
- **Keybinds:** every action is bindable to a keyboard key or mouse button (including MOUSE4/5), in hold / toggle / press
  mode, with conflict warnings.
- **Profiles:** readable JSON files with a forgiving loader (bad values are fixed and reported, never fatal), a read-only
  `default`, and the last profile loaded automatically.
- **Panic (END):** instantly disables everything, unfreezes all values and restores your original FOV.
- **Robust:** start it before or after the game, close and restart the game, switch matches: it reattaches by itself and
  never crashes on a bad read.

## Requirements
- Windows 10/11, **Python 3.11+** (64-bit is fine: see [section 3](#3-bytes-pointers-and-32-bit)).
- **AssaultCube 1.3.0.2** (the exact version: every offset is for this build), running **windowed or borderless**.
  The overlay can't draw over exclusive fullscreen.
- Python packages: [`pymem`](https://github.com/srounet/Pymem) (memory), [`PyQt5`](https://www.riverbankcomputing.com/software/pyqt/)
  (menu + overlay) and [`pytest`](https://pytest.org) (tests). Win32 calls use the standard library's `ctypes`.

## Install
```powershell
python -m pip install -r requirements.txt
python -m pip install -e .          # editable install, so `actrainer` is importable from tools and tests
```

## Run
1. Start AssaultCube and begin an **offline bot match**.
2. Run `python -m actrainer`. The menu opens, and the header shows **● Attached · N bots · 60 Hz**.
   Pick a section in the left sidebar.
3. Press **INSERT** to hide or show the menu at any time, including from inside the game.

The trainer can be started before the game. It attaches automatically within about a second of the game starting, and
reattaches if the game is restarted. Logs go to the console and to `logs\actrainer.log`.

> If the game runs as administrator, run the trainer as administrator too. Windows doesn't let a normal process open an
> elevated one.

## Using the menu
| Page | What's there |
|---|---|
| **Aimbot** | Enable, activation key and mode (default: hold **right mouse button**), aim at head/body, priority, max distance, team check (leave off in free-for-all), FOV radius + "draw FOV circle", smoothing (1 = instant snap) |
| **ESP** | Enable, toggle key, team mode (off for free-for-all), enemies only, styles (click the chips to combine), line thickness, enemy/team colours, info extras, snapline origin |
| **Player** | Game FOV (slider, Set now, Keep applied); stats and ammo, each with target, live "Now" value, Set now, key and Freeze |
| **Keybinds** | Every bindable action by category. Click a key button, then press any key or mouse button; **Esc** clears. Conflicts show in red, and the sidebar entry gets a ⚠ |
| **Settings** | Profiles (Save / Save as / Load / Rename / Delete), Reset to defaults, tick rate, overlay FPS, menu hotkey, status panel |

### Choosing colours
Click any colour chip (e.g. **#FF4040 · 100%**) to open the picker:
- **Presets:** one click; your current opacity is kept.
- **Colour square + hue bar:** for any custom colour.
- **Opacity:** slider in %. The swatches sit on a checkerboard so you can see transparency.
- **Hex:** type `#RRGGBB` or `#RRGGBBAA`.

The colour applies **live** while the picker is open, so you can judge it on real bots. **Apply** (or clicking outside)
keeps it; **Cancel** or **Esc** puts the old colour back. Click **Old** to jump back to the original.

### Default hotkeys
| Key | Action |
|---|---|
| INSERT | Show / hide the menu |
| END | **Panic**: aimbot and ESP off, every freeze off, original FOV restored, toggles reset |
| Right mouse (hold) | Aimbot (when enabled) |

Everything else is unbound by default: the aimbot and ESP toggles, Set now / Freeze for every value, the game FOV and a
Quit action can all be bound on the Keybinds page.

### Profiles
- Changes apply immediately but are only saved when you click **Save**. A `*` in the title means unsaved changes.
- `default` is read-only: use **Save as** to create your own. The last profile you used loads automatically on startup.
- Profiles are readable JSON files in `profiles\`. If one contains invalid values, they're reset or clamped and you're
  told exactly which.

## Troubleshooting
| Problem | Fix |
|---|---|
| "Not attached" | Start AssaultCube. If the game runs as administrator, run the trainer as administrator too. |
| "Attached · not in a match" | Start or join an offline bot match. The main menu has no player to read. |
| Menu not clickable when it pops up | Press Esc in-game to free the cursor, then INSERT again. |
| No overlay | Run the game windowed or borderless, enable ESP, and keep the game (or the menu) focused. |
| ESP boxes offset | Check Windows display scaling isn't overriding DPI for Python. Run `python tools\phase8_view_matrix.py`: it should say `OK`. |
| "External Cheat is already running" | Another copy is open. Use INSERT to find its menu, or quit it. |
| Values aren't written | Values are never written while you're dead or outside a match (the notice line says why). Freezes resume on respawn. |
| After a game update | Run `tools\phase1_local_player.py`, `phase2_entities.py` and `phase8_view_matrix.py` to check the offsets still work. |

## Debug tools
Small scripts in `tools\`, one per build phase. Each prints live values from the game, so you can watch one piece working
on its own. All of them only **read** memory.

| Script | What it shows |
|---|---|
| `phase1_local_player.py` | Your position, view angles, health and team, live, with auto-reattach |
| `phase1_dead_diag.py` | Press F9 to snapshot the player struct (alive / dead / alive) and print every offset that changed |
| `phase2_entities.py` | A live table of every bot (name, health, armour, team, head, distance, state) + the raw pointer slots |
| `phase3_angles_check.py` | Your real view angles next to the angles the maths computes for the bot nearest your crosshair |
| `phase4_keybinds.py` | The keybind engine reacting to real keys (hold / toggle / press, mouse buttons) |
| `phase8_view_matrix.py` | The centre check (your view direction must project to the screen centre), the FOV from the matrix, the nearest bot's head/feet in pixels |
| `readme_shots_game.py` / `readme_shots_menu.py` | Regenerate the README screenshots |

## Tests
```powershell
python -m pytest
```
**316 tests** cover the maths (angles, projection, skeleton), aimbot, ESP, player values, game FOV, settings and profiles,
keybinds, the controller, the overlay painter and the menu. They need no game and open no windows (Qt runs offscreen),
and the whole suite runs in about a second. [Section 17](#17-testing-without-the-game) explains how.

## Project layout
```
pyproject.toml            package metadata (src layout, editable install) + pytest config
requirements.txt          pymem, PyQt5, pytest
profiles/default.json     the default profile (a test keeps it equal to the code defaults)
tools/                    one live debug script per phase + README screenshot scripts
docs/DEVLOG.md            dated build diary, including every bug and its fix
CLAUDE.md                 the project's memory: rules, architecture, offsets, gotchas, decision log
src/actrainer/
  main.py                 entry point: logging, DPI awareness, single-instance lock, wiring, quit
  config.py               every constant that isn't an offset (ranges, caps, sanity limits, paths)
  offsets.py              EVERY memory offset, in one file
  memory/                 THE ONLY code that imports pymem: attach, typed reads/writes
  game/                   game memory → plain data: player struct, entity list, view matrix, game state
  maths/                  PURE: vectors, aim angles, world-to-screen, skeleton
  features/               PURE: aimbot, ESP (→ draw primitives), player values, game FOV
  settings/               PURE models + JSON store (forgiving load, migrations) + the signal hub
  input/                  PURE: key names, action registry, keybind engine
  app/                    the controller: the 60 Hz tick that ties it all together
  overlay/                the transparent click-through window + the painter
  ui/                     the PyQt5 menu: theme, widgets, one file per page
  winapi/                 THE ONLY code that makes Win32 calls (ctypes)
tests/                    mirrors src/actrainer, plus fakes (fake game memory, AC-style matrices)
```

---

## How it works (the educational part)

This project was built to learn how a game stores its world in memory, and how to turn that data into an aimbot and an
ESP with some vector maths, all from a separate program. This section walks through every piece in the order it was
built. The addresses and numbers are the real ones from AssaultCube 1.3.0.2, and file links point to where each idea
lives in the code.

### 1. External vs internal: what a separate process can do

There are two ways to build a trainer:

| | **External** (this project) | **Internal** ([the follow-up](https://github.com/BigH018/internal-assault-cube)) |
|---|---|---|
| What it is | A normal program running next to the game | A DLL loaded *into* the game's process |
| Reading memory | `ReadProcessMemory`: a system call per read | A plain pointer dereference |
| Timing | Its own timer (60 Hz here), out of step with the game's frames | Runs inside the game's frame, on the game's thread |
| Drawing | A transparent window laid over the game | Draws into the game's own frame |
| What it can change | **Values**: health, ammo, view angles, FOV | Values, *and the game's code*: call its functions, hook them, patch instructions |
| If it crashes | Only the trainer closes; the game keeps running | The game crashes with it |
| Language | Anything that can call the Windows API (Python here) | Something that compiles to a DLL (C++) |

External is the best place to start. A mistake can't crash the game, you can use Python, and every concept (memory
layout, pointers, maths, projection) carries straight over to internal work later.

The limit is in the "what it can change" row. An external trainer only sees the game's **data**, never its logic. Some
things that are easy from inside are hard or impossible from outside:
- **"Is this bot visible?"** The game has a function for that (`TraceLine`), but an external program can't call it. You'd
  have to rebuild the map's geometry yourself. That's why this ESP draws every bot, through walls.
- **God mode.** Freezing health at 100 works until a sniper headshot does 100+ damage in one hit: you die between two
  freezes. Stopping the hit needs a hook on the game's damage function, which needs code inside the game.

### 2. Attaching to the game

Every running program has its own private **address space**: address `0x0050F4F4` in one process has nothing to do with
the same address in another. Windows lets a program with the right permissions **open** another process and read or
write its memory. That's all an external trainer is. [`memory/process.py`](src/actrainer/memory/process.py) does it
through `pymem`:

```
1. find the process        pymem lists running processes and finds "ac_client.exe"   → process id
2. open it                 OpenProcess(access rights, pid)                           → a handle
3. find the module base    enumerate the modules loaded in the game                  → where ac_client.exe sits
4. read / write            ReadProcessMemory(handle, address, size)
                           WriteProcessMemory(handle, address, bytes)
```

**The module base.** The game's code and its global variables live inside `ac_client.exe`, which Windows loads at a
base address (`0x00400000` for this game: it's built without ASLR, so it never moves). Every static address in
[`offsets.py`](src/actrainer/offsets.py) is an offset from that base, e.g. the local player pointer is at
`base + 0x18AC00`. Writing offsets relative to the base (not as absolute addresses) is the habit to keep: most games *do*
move between runs.

**Admin rights.** `OpenProcess` fails if the game runs as administrator and the trainer doesn't. Windows won't let a
lower-privilege process open a higher one.

**Is the game still there?** The trainer checks once a second by reading two bytes at the module base. Every Windows
executable starts with the letters `MZ` (the DOS header), so if that read still returns `MZ`, the process is alive and the
handle still works. If not, the trainer detaches and tries to attach again once a second until the game comes back.

**Finding the window.** The overlay and the focus checks also need the game's **window**. `EnumWindows` lists every
top-level window, and [`winapi/win32.py`](src/actrainer/winapi/win32.py) keeps the visible, titled, unowned one whose
process id matches the game.

### 3. Bytes, pointers and 32-bit

`ReadProcessMemory` returns raw **bytes**. You decide what they mean. Two rules make that work:

**x86 is little-endian:** the lowest byte comes first. Health 100 (`0x00000064`) is stored as `64 00 00 00`. A float is 4
bytes of IEEE 754: `1.0` is `0x3F800000`, stored as `00 00 80 3F`.

**AssaultCube is a 32-bit program, so a pointer is 4 bytes**, even though our Python is 64-bit. Reading a pointer as 8
bytes would glue it to the next 4 bytes of memory and send every pointer chain after it into nowhere. So the trainer
never lets a library guess sizes: every value is unpacked with an explicit `struct` format
([`memory/process.py`](src/actrainer/memory/process.py)):

```python
_U32 = struct.Struct("<I")   # "<" = little-endian, "I" = unsigned 32-bit: POINTERS
_I32 = struct.Struct("<i")   # signed 32-bit: health, ammo, team...
_F32 = struct.Struct("<f")   # 32-bit float: positions, angles, FOV

def read_u32(self, address: int) -> int:
    """Read an unsigned 32-bit int. Use this for POINTERS in the 32-bit game."""
    return _U32.unpack(self.read_bytes(address, _U32.size))[0]
```

A 64-bit program can read a 32-bit one without problems. The game's addresses all fit in 32 bits, so they work as
Python ints like any other number.

`memory/` is the **only** package that imports `pymem`. Everything above it sees plain ints, floats, bytes and two
exception types (`AttachError`, `MemoryAccessError`), so the rest of the code never knows how memory is accessed.

### 4. Pointer chains and the player struct

**Pointer chains.** Players are created while the game runs, so their addresses change every match. The game keeps a
*static* variable (one at a fixed place inside `ac_client.exe`) that *points* to the local player. Follow it:

```
base + 0x18AC00  ──read 4 bytes (u32)──►  0x009DD2C8     the address of your player struct
0x009DD2C8 + 0xEC ──read 4 bytes (i32)──►  100           your health
```

That's a chain of length 1. Many games need several hops (`[[[base + a] + b] + c]`), but the idea is the same: each
step reads a pointer and adds the next offset.

**Structs.** The player is a C++ object (`playerent` in the game's source): one block of bytes where every field sits at
a fixed offset. These are the ones this project uses:

| Offset | Field | Type |
|---|---|---|
| `0x04` | head position (the **eye**, really) | 3 floats (x, y, z; z is up) |
| `0x28` | feet position | 3 floats |
| `0x34` / `0x38` | yaw / pitch (view angles, degrees) | float, float |
| `0xEC` / `0xF0` | health / armour | int, int |
| `0x108`–`0x11C` | reserve ammo, one per weapon (pistol, carbine, shotgun, SMG, sniper, assault) | 6 ints |
| `0x12C`–`0x140` | magazine ammo, same order | 6 ints |
| `0x144` / `0x148` | grenades / akimbo ammo | int, int |
| `0x205` | name | 16 chars, null-terminated |
| `0x30C` | team | int |
| `0x318` | dead flag | int (non-zero = dead) |

**One read per player.** Reading those fields one at a time would be ~20 system calls per player, per tick. Instead the
trainer reads the whole block from `0x00` to `0x31C` in **one** call and unpacks every field locally
([`game/player.py`](src/actrainer/game/player.py)):

```python
def read_player(proc, address):
    return parse_player(proc.read_bytes(address, offsets.PLAYER_READ_SIZE), address)   # 0x31C bytes, one call

def parse_player(buf, address):                       # pure: unit-tested with fake bytes
    return PlayerSnapshot(
        head=_vec3_at(buf, offsets.HEAD_POS),         # struct.unpack_from("<3f", buf, 0x04)
        health=_i32_at(buf, offsets.HEALTH),          # struct.unpack_from("<i", buf, 0xEC)
        dead=_i32_at(buf, offsets.DEAD) != 0,
        ...
    )
```

The result is a frozen `PlayerSnapshot`: plain data that the aimbot, ESP and menu use without ever touching memory again.

### 5. The entity list: finding every bot

The bots live in the game's `vector<playerent*> players`. A C++ vector in this build is three 4-byte values sitting
together, and the game declares it right after `player1`:

```
base + 0x18AC00   playerent* player1      your player (section 4)
base + 0x18AC04   playerent** buf         pointer to an array of player pointers
base + 0x18AC08   int capacity            how many slots are allocated
base + 0x18AC0C   int count               how many slots are in use (including yours)
```

So reading every bot is two hops ([`game/entities.py`](src/actrainer/game/entities.py)):

```python
count = proc.read_i32(base + offsets.PLAYER_COUNT)                # e.g. 8
list_address = proc.read_u32(base + offsets.ENTITY_LIST_PTR)      # the array
raw = proc.read_bytes(list_address, count * 4)                    # every slot in ONE read
pointers = struct.unpack(f"<{count}I", raw)                       # 8 x uint32
```

Then each pointer is read as a player (section 4). **Slot 0 is empty**: it stands for you. The rest are bots, *if* they
pass a few sanity checks. Memory you read from a game can be garbage at any moment: a slot being reused, a match
loading, a bot leaving. So nothing is trusted:

| Check | Why |
|---|---|
| Pointer between `0x10000` and `0x7FFFFFFF` | Below 64 KiB is never a valid allocation on Windows; above is outside 32-bit user space |
| Not your own address | You're in the list too |
| Positions finite and within ±10 000 units | Garbage bytes decode as huge floats, NaN or infinity |
| Alive bots: health 0–100. Dead bots: down to −1000 | **Health goes negative when you die** (−54 was observed), so a 0–100 filter would throw dead bots away as garbage |
| Count clamped to 64 | A garbage count could otherwise mean reading thousands of "players" |

One bad slot is logged and skipped, never fatal. The other bots still show up.

**A finding about teams.** In free-for-all deathmatch, every bot still has a team value (0 or 1), and some share yours.
A "skip teammates" check would wrongly ignore them. That's why team check (aimbot) and team mode (ESP) are user switches
and off by default.

### 6. Finding offsets: a real bug from this project

Offsets come from somewhere: public tables, a memory scanner such as Cheat Engine, or reading the game's source code
(AssaultCube is open source). But an offset that "works" can still be the wrong one. This project had exactly that bug.

**The symptom.** The first local-player pointer, `base + 0x17E0A8`, worked perfectly... until you died. Then the `dead`
flag stayed `0` and the name came back empty.

**The diagnostic.** [`tools/phase1_dead_diag.py`](tools/phase1_dead_diag.py) takes three snapshots of the whole player
struct when you press F9: **alive → dead → alive again**, and compares them byte by byte. A value that's the same in
both "alive" snapshots but different while dead is a **strong** candidate for something death-related. Comparing A/B/A
instead of just A/B filters out the noise from timers and movement.

**What it showed.** The **pointer itself** changed on death: `0x009DD2C8` → `0x00595410`. The "dead" snapshot had a
different object type, an empty name, and the text `packages\models\weapons\grenade\static\shadows.dat` where the ammo
should be. We weren't reading a player at all.

**The cause.** `0x17E0A8` is the game's **camera** pointer (`camera1`). While you're alive the camera follows you, so it
points at your player. When you die it switches to a separate death-cam object.

**The fix: scan for the real pointer.** The player's address (`0x009DD2C8`) was known, so the next step was to search
the game's static memory for every 4-byte slot holding that value. Four hits came back. One of them, `base + 0x18AC00`,
sat right before something that looked like a vector (a pointer, then 16, then 8: capacity and count). That matches the
game's source exactly: `playerent *player1;` declared right before `vector<playerent*> players;`. The new pointer stayed
the same across a death, and `dead` went `0 → 1 → 0` as it should. The `dead` offset had been right all along.

**Lesson:** test offsets in more than one game state (alive/dead, in a match/in the menu, before/after a map change).
"Right most of the time" can still be the wrong variable. Every offset change in this project follows a rule: prove it
with a diagnostic, keep the old value in a comment, and log the evidence in [`docs/DEVLOG.md`](docs/DEVLOG.md). The old
value lives on in [`offsets.py`](src/actrainer/offsets.py) as `CAMERA_PTR`, with a warning not to use it.

### 7. Aim angles: AssaultCube's yaw convention

Your view direction is two angles: **yaw** (left/right) and **pitch** (up/down), in degrees. To aim at something you need
the reverse: given a target position, which yaw and pitch point at it?

**Read the game's convention, don't guess it.** The game's source has `vecfromyawpitch()`, which turns angles into a
direction:

```
forward = ( sin(yaw)·cos(pitch),  −cos(yaw)·cos(pitch),  sin(pitch) )
```

So yaw 0 faces **−y**, yaw 90 faces **+x**, and pitch is positive upwards. Inverting that for a target offset
`d = target − eye` ([`maths/angles.py`](src/actrainer/maths/angles.py)):

```python
d = target - eye
yaw   = degrees(atan2(d.x, -d.y))            # AC convention: measured from -y
pitch = degrees(atan2(d.z, hypot(d.x, d.y))) # height difference vs horizontal distance
```

`atan2(d.x, −d.y)` is the same as the "standard" `atan2(d.y, d.x) + 90°`. That's the famous **+90° yaw offset**:
standard maths measures angles from the +x axis, AssaultCube measures them from −y. Yaw is then wrapped into 0–360° and
pitch clamped to ±90°.

**The aim origin is your eye** (`head`, offset `0x04`), not your feet: the camera sits at your eye, so that's where the
line to the target has to start.

**Checked against the real renderer.** The tests build the view matrix exactly the way the game's `transplayer()` does
(same OpenGL rotations, in the same order) and check that a point straight along `direction_from_angles(yaw, pitch)`
projects to the exact centre of the screen, for 7 different yaw/pitch combinations. So the angle maths and the
projection maths (section 9) are tested against each other.

### 8. The aimbot: filter, prioritise, smooth, write

Each tick the aimbot ([`features/aimbot.py`](src/actrainer/features/aimbot.py)) runs four steps. It's a **pure**
function: it gets a snapshot of the game and the settings, and returns new angles. It never touches memory itself.

**1. Filter.** For every bot, work out the aim point (the head, or 60% of the way from feet to head for "body", which
also scales when the bot crouches), the angles to it, its distance and its **angle from your crosshair**. Drop dead bots,
teammates (if team check is on), bots beyond max distance and bots outside the FOV radius.

The angle from your crosshair is the *true* angle between two view directions, from the dot product:

```python
cos_angle = dot(direction_from_angles(view), direction_from_angles(target))
angle = degrees(acos(clamp(cos_angle, -1, 1)))     # clamp: rounding can push the dot a hair past ±1
```

Just subtracting yaws breaks when you look steeply up or down. At pitch 89°, two directions 180° apart in yaw are really
only 2° apart. The dot product doesn't care.

**2. Prioritise.** Sort what's left by the chosen priority: closest to crosshair, closest distance, or lowest health.
Ties are broken by a second key (angle, or distance), so the pick is always the same for the same input and the aim
doesn't flicker between two equal targets.

**3. Smooth.** Snapping instantly looks robotic. Each tick, the view moves `1/smoothing` of the *remaining* angle, so it
moves quickly at first and slows down as it arrives:

```python
new_yaw   = current.yaw   + yaw_delta(current.yaw, target.yaw) / smoothing     # smoothing 1 = instant snap
new_pitch = current.pitch + (target.pitch - current.pitch) / smoothing
```

`yaw_delta` handles the wrap-around: going from 350° to 10° is a **+20°** turn through 0, not −340°. The difference is
wrapped into (−180°, 180°] first, so the view always takes the short way round.

One catch: this moves a fixed fraction **per tick**, so a higher tick rate aims faster. (The internal follow-up runs once
per *frame* and had to make it time-based instead.)

**4. Write.** Yaw (`0x34`) and pitch (`0x38`) are neighbours in memory, so both go out in **one** 8-byte write
(`struct.pack("<2f", yaw, pitch)`). The game never renders a frame with the new yaw and the old pitch.

**Safety rule:** the controller only runs the aimbot when it's enabled, the key is active **and the game window is
focused**. Holding right mouse over the menu (or any other program) never moves your view.

### 9. World-to-screen: the view matrix

To draw a box around a bot you need to know where its head and feet appear **on your screen**. The game already works
this out every frame to render the world, using a 4×4 **view-projection matrix**. It keeps that matrix in memory: 16
floats stored **in place** at `base + 0x17DFD0` (not behind a pointer). We read the same 16 floats and do the same maths
([`maths/projection.py`](src/actrainer/maths/projection.py)).

**Step 1: world → clip space.** Multiply the point `(x, y, z, 1)` by the matrix. OpenGL stores matrices
**column-major**, so the element in row r, column c is at index `c*4 + r`:

```
clip_x = m[0]·x + m[4]·y + m[8]·z  + m[12]
clip_y = m[1]·x + m[5]·y + m[9]·z  + m[13]
clip_w = m[3]·x + m[7]·y + m[11]·z + m[15]      # ≈ how far in front of the camera the point is
```

Read it as row-major by mistake and you get boxes that slide around the screen as you turn. It's the most common
world-to-screen bug.

**Step 2: behind the camera?** If `clip_w` is tiny or negative, the point is behind you. Dividing by it would *mirror*
the point onto the screen, so anything with `clip_w < 0.001` is skipped.

**Step 3: perspective divide.** Far things look smaller because everything is divided by distance:
`ndc = (clip_x / clip_w, clip_y / clip_w)`. These "normalised device coordinates" run from −1 to 1 across the screen.

**Step 4: to pixels.** Screen y grows **downwards** but NDC y grows upwards, so y is flipped:

```
screen_x = (ndc_x + 1) / 2 · width
screen_y = (1 - ndc_y) / 2 · height
```

**Proving it's right.** A point placed straight along your own view direction must land in the exact centre of the
screen. On a 1920×1080 game window it lands at **(960.0, 540.0)**. That single check confirms the matrix address, the
column-major layout and the yaw/pitch maths all agree ([`tools/phase8_view_matrix.py`](tools/phase8_view_matrix.py)).

**What the matrix tells you about the FOV.** The rotation part of the matrix keeps lengths, so the length of row 0 is the
projection's x scale, `1 / tan(hfov / 2)`. The live matrix had a row 0 length of exactly **1.000** (`1 / tan(45°)`, so
90° horizontal) and a row 1 length of **1.7777** (16:9). That proved the game's FOV setting at `base + 0x18A7CC` is the
**horizontal** FOV, which the FOV circle (section 10) depends on.

**Before the first frame**, the matrix can be all zeros. A sanity check (16 finite numbers, not all zero) runs before
anything is projected.

### 10. The ESP: boxes, skeletons and the FOV circle

[`features/esp.py`](src/actrainer/features/esp.py) turns the game state into a list of **shapes** (lines, rectangles,
filled rectangles, circles, text). It never draws anything itself. The overlay (section 11) just paints whatever list it
gets. That split is what lets the ESP be unit-tested without a game or a window.

**From two points to a box.** Project the feet and the top of the head. The stored head position is the *eye*, so 0.8
units are added on top. The vertical distance between the two screen points is the box height, and the width is 45% of
it, roughly a person's proportions. If either point is behind the camera, the bot is skipped.

**Styles and extras** all hang off that box: corner box (25% of each side), head circle (radius 9% of the box height),
a health bar on the left that fades from green to red, name, health number, distance, and a snapline from the bottom or
centre of the screen to the bot's feet. Bots are drawn **furthest first**, so nearer ones end up on top, and the
aimbot's current target is drawn thicker.

**The skeleton.** The game stores no bone data, so the stick figure is *approximated*
([`maths/skeleton.py`](src/actrainer/maths/skeleton.py)): each joint sits at a fixed fraction of the player's height
(neck 86%, shoulders 82%, hips 50%, knees 26%), offset sideways and forwards using the player's facing direction. Then
each joint is projected like any other point. Because it's based on height, it shrinks properly when a bot crouches.

A bug the tests caught: AssaultCube's world is **left-handed** (the renderer calls it "Z-up LH quake style"), so a
player's right is `up × forward`. The textbook `forward × up` put the arms on the wrong side.

**The FOV circle.** The aimbot's FOV is measured in **degrees** (so it works at any resolution), but the circle is drawn
in **pixels**. In a perspective view, a ray at angle `a` from the centre lands this far from the centre:

```
radius_px = tan(a) / tan(hfov / 2) · width / 2
```

with `hfov` read from the game every tick. So the circle stays correct when you change the game FOV, and a bot inside the
circle is exactly a bot the aimbot is allowed to pick.

### 11. The overlay window

The ESP is drawn on a separate window laid exactly over the game
([`overlay/window.py`](src/actrainer/overlay/window.py)). Making that window behave takes a few tricks:

| Requirement | How |
|---|---|
| Only the drawings visible | Qt `WA_TranslucentBackground` (per-pixel alpha); each frame first clears every pixel to fully transparent |
| No title bar, always above the game | `FramelessWindowHint`, `WindowStaysOnTopHint` |
| **Clicks go to the game, not the overlay** | Qt's `WA_TransparentForMouseEvents` only affects Qt. Windows itself still hit-tests the window unless it also has the extended styles `WS_EX_LAYERED \| WS_EX_TRANSPARENT` (set with `SetWindowLongPtrW`) |
| Never steals focus, no taskbar button | `WS_EX_NOACTIVATE`, `WS_EX_TOOLWINDOW`, `WA_ShowWithoutActivating` |
| Exactly over the picture | Sized to the game's **client area** (`GetClientRect` + `ClientToScreen`), not the window with its frame. Followed every tick, so moving the game window moves the overlay |
| Lined up on high-DPI screens | The process is made **DPI-aware** before Qt starts. Without that, Windows scales the window on a 150% display and every box lands in the wrong place |

**Two clocks.** The controller makes a new frame of shapes at the tick rate (60 Hz), and the window repaints on its own
timer at the overlay FPS. Changing one doesn't slow the other down.

**When it shows.** The overlay is visible only while there's something to draw **and** the game or the menu is focused.
Alt-tab to a browser and it disappears. While the menu is focused it stays, so you can watch ESP changes as you make them.

**The limits of an overlay.** It can't draw over *exclusive* fullscreen (the game owns the screen then), so the game must
run windowed or borderless. And it's always slightly behind: the trainer reads the matrix on its own timer, not in step
with the game's frames, so during a fast turn the boxes trail by up to a frame. (The internal version reads the matrix
inside the game's frame and draws into it, so it has neither problem.)

### 12. Player values, freezes and the game FOV

**Setting a value** is one 4-byte write: health is `player + 0xEC`. The features never see offsets. They name fields
with ids (`health`, `mag:pistol`, `reserve:sniper`), and only [`game/local_player.py`](src/actrainer/game/local_player.py)
maps ids to offsets.

**Freeze** is the same write repeated every tick. [`features/player_values.py`](src/actrainer/features/player_values.py)
plans the writes and only includes fields whose value actually *differs*, so a freeze costs nothing while the value is
already right. Every target is clamped to a range in [`config.py`](src/actrainer/config.py) (no negative ammo).

Lessons from testing:
- **No writes while dead.** Writing health to a dead player can confuse the game's death state. Freezes pause while
  you're dead and resume on respawn; "Set now" while dead is refused with a notice.
- **Don't validate the local player with health 0–100.** The trainer can set health to 999, and it would then decide
  your player is "invalid" and stop working. The local player is validated by pointer and position only.
- **"Set now" doesn't write from the button click.** The click queues a request, and the next tick applies it inside its
  normal read → decide → write cycle. All memory access stays in one place, on one timer.

**Game FOV.** The game's FOV is a float at `base + 0x18A7CC`. Writing it changes the view immediately, and testing showed
the game **never clamps it**: 30, 60, 110, 150 and even 170 all rendered. The console's own `/fov` limits don't apply to a
memory write, so the trainer's slider range (30–150) is the only guard. The FOV before the first change is remembered
and written back on panic and on quit. That matters because the game saves its FOV to its config file on exit: without
the restore, the trainer's FOV would become your permanent setting.

### 13. Global hotkeys and the keybind engine

**Why not Qt key events?** Qt only gets keys while one of *its* windows is focused. In a game, AssaultCube is focused, so
INSERT would never reach the menu. Instead, the trainer **polls** `GetAsyncKeyState` every tick. It reports whether a key
or mouse button is down right now (the high bit, `0x8000`), whichever window is focused. Keyboard keys and mouse buttons
(LMB, RMB, MMB, MOUSE4, MOUSE5) work the same way.

**From "is down" to actions** ([`input/keybinds.py`](src/actrainer/input/keybinds.py), pure). Each tick the engine gets
the set of keys that are down and compares it with last tick's:

```python
just_pressed = down_now - down_last_tick       # set difference = keys that went down THIS tick (rising edges)
```

Then every bind is one of three modes:
- **HOLD**: active while the key is down (the aimbot's default).
- **TOGGLE**: each rising edge flips it on/off.
- **PRESS**: fires once, on the rising edge (menu, panic, set now, every on/off switch).

**Bind capture.** Clicking "press a key" on the Keybinds page polls the same way. The catch: the click that starts the
capture *is itself* a left-click, so the capture first waits until every key is released, or every bind would become
LMB. Esc clears a bind, and while a capture is running the engine still tracks keys but fires nothing, so the key you
just bound doesn't trigger its action the moment capture ends.

**What can't be bound:** the scroll wheel (it's not a key that can be held, so it can't be polled), and the generic
Shift/Ctrl/Alt codes (they fire together with the Left/Right versions, which *are* bindable). Two actions on one key are
allowed but highlighted in red, with a ⚠ on the sidebar.

### 14. A menu over a game that grabs the mouse

While you play, AssaultCube **captures the mouse**: the cursor is hidden and locked to the window. Pressing INSERT has to
bring the menu to the front *and* get the cursor back.

**The foreground lock.** Windows doesn't let a background program pull itself in front of the program you're using
(so pop-ups can't steal your typing). Qt's `activateWindow()` just flashes the taskbar button. The workaround
([`winapi/win32.py`](src/actrainer/winapi/win32.py)): briefly attach our thread's input queue to the foreground
thread's, so Windows treats us as part of the program you're using, and then bring the menu forward:

```python
attached = AttachThreadInput(our_thread, foreground_thread, True)
try:
    BringWindowToTop(menu); SetForegroundWindow(menu); SetFocus(menu)
finally:
    if attached:
        AttachThreadInput(our_thread, foreground_thread, False)
```

When AssaultCube loses focus it releases the mouse by itself, so the menu is immediately clickable. Hiding the menu
gives focus back to the game, which grabs the mouse again. (Verified in-game. If it ever fails, Esc in the game frees
the cursor.)

### 15. Settings and profiles

- **One shared `Settings` object.** The menu only *edits* it. The controller *reads* it every tick. So every change
  applies live, and the UI never touches game memory.
- **Every range is defined once.** A setting carries its range in its definition
  ([`settings/models.py`](src/actrainer/settings/models.py)): `fov_deg: float = ranged(15.0, config.AIM_FOV_RANGE)`.
  The slider takes its limits from it, and the profile loader clamps with it, so they can never disagree.
- **Forgiving load** ([`settings/store.py`](src/actrainer/settings/store.py)). Profiles are hand-editable JSON with
  readable values (`"INSERT"`, not `45`). Unknown keys are ignored, missing keys keep their defaults, wrong types and bad
  colours fall back to the default, and numbers are clamped. Every fix becomes a warning you're shown. Only a missing
  file or broken JSON is an error.
- **Atomic saves:** write `name.json.tmp`, then `os.replace` it over the real file. A crash mid-save can't leave half a
  profile.
- **Schema versions:** every profile has a `schema_version`, and a migration table upgrades old profiles on load if a
  setting is ever renamed or moved.
- **Explicit save.** Changes apply live but are written to disk only on Save, with a `*` in the title until then.
  `default` is read-only, and a test keeps `profiles/default.json` equal to the code defaults.

### 16. Never crash: errors, reattach and one instance

The game can close, restart, load a map or sit in its main menu at any moment. Every one of those makes reads fail or
return garbage, and none of them may crash the trainer:

- **A read error skips the tick.** Every memory error becomes a `MemoryAccessError`. The controller catches it, logs
  it, and tries again next tick. The whole tick is also wrapped in a catch-all that logs the traceback.
- **No player, no problem.** Outside a match the local player pointer is null or garbage, so the game state is `None`
  and every feature simply has nothing to do. The status pill says "not in a match".
- **Reattach.** Not attached → try once a second. Attached → check for `MZ` once a second (section 2). The game can be
  restarted as often as you like.
- **PyQt5 aborts on exceptions in callbacks.** Since PyQt 5.5, an unhandled Python exception in a slot or `paintEvent`
  kills the whole app. A `sys.excepthook` logs it with a traceback instead.
- **Single instance.** Two trainers fighting over the same game would be chaos, so a `QLockFile` in the temp folder
  stops a second copy (and spots a stale lock from a crashed copy by its process id). A bug found here: the second copy
  opened the log file *before* checking the lock, and wiped the running trainer's log. Now logging to file only starts
  once the lock is held.
- **Precise timers.** Qt's default timer on Windows ticks in ~15.6 ms steps, which makes 60 Hz uneven.
  `Qt.PreciseTimer` fixes it.

### 17. Testing without the game

316 tests run in about a second, with no game and no windows. Three ideas make that possible:

**Pure code wherever possible.** The maths, aimbot, ESP, player values, settings and keybind engine take plain data and
return plain data. No memory, no Qt, no Windows calls. The rules are enforced by the layout: only `memory/` imports
`pymem`, only `winapi/` calls Win32, and the UI never touches memory.

**A fake game.** [`tests/helpers/fake_game.py`](tests/helpers/fake_game.py) builds player structs byte by byte at the real
offsets, and a `FakeProcess` with the same read/write methods as the real one serves them from
fake memory regions. The entity reader, the game-state reader and the whole controller tick are tested against it, including null
slots, garbage pointers, dead bots and unreadable memory.

**The game's own maths, rebuilt.** [`tests/helpers/gl_matrix.py`](tests/helpers/gl_matrix.py) builds the view matrix
with the same OpenGL calls as the game's renderer (`transplayer()` plus `gluPerspective`). So the projection is tested
against real AssaultCube-style matrices, and the angle maths against the projection (section 7).

The UI is tested too: Qt runs on its **offscreen** platform, and the overlay painter is checked by rendering shapes into
an image and testing the pixels. (Offscreen Qt draws no text unless it's told where the fonts are:
`QT_QPA_FONTDIR=C:/Windows/Fonts`.)

### 18. How it all fits together

```
           settings  ◄──── menu (edits settings only, never touches memory)
              │
              ▼
 game memory ─► read local player, bots, view matrix, FOV ─► aimbot ─────────► write view angles
   (pymem)        (one GameState per tick)                  ├► player values ──► write health / ammo
                                                            ├► game FOV ───────► write FOV
                                                            └► ESP ─► shapes ──► overlay window
 keyboard / mouse ─► keybind engine (hold / toggle / press) ─► menu, panic, features on/off
```

A `QTimer` runs this loop 60 times a second ([`app/controller.py`](src/actrainer/app/controller.py)):

```
1. poll keys         GetAsyncKeyState → keybind engine → menu toggle, panic, set now, freezes, toggles
2. attached?         if not, try again (once a second) and stop here
3. read              local player + live bots + view matrix + FOV → a frozen GameState (None outside a match)
4. aimbot            enabled + key active + game focused → compute_aim → one 8-byte angle write
5. values / FOV      queued "Set now" + freezes → only the writes that change something
6. ESP               build_esp(state) → shapes + the game's client rect → the overlay
7. status            2× a second: attached, bots, tick rate, live values → the menu
```

### 19. What I learned, phase by phase

| Phase | Built | The lesson |
|---|---|---|
| 1 | Attach, read the local player, live debug print | Pointers in a 32-bit game are 4 bytes; read a struct once and unpack it locally; the camera pointer isn't the player pointer (section 6) |
| 2 | Entity list, every bot | Health goes negative on death; FFA bots still have team values; never trust a slot |
| 3 | Maths: angles, projection, skeleton | Derive the yaw convention from the game's source; test angles and projection against each other; AC's world is left-handed |
| 4 | Settings, profiles, keybind engine | Ranges defined once; forgiving loads; edge detection with set difference; a separate action registry avoids an import cycle |
| 5 | The menu | Foreground lock and `AttachThreadInput`; bind capture must wait for release (the click is a key too); hiding the last window mustn't quit the app |
| 6 | Controller + aimbot | True angular distance; shortest-path smoothing; one 8-byte write; only aim while the game is focused |
| 7 | Player values | Write only what differs; never write while dead; button clicks queue requests, the tick does the writing |
| 8 | View matrix | Column-major layout; the screen-centre proof; the FOV setting is horizontal (read off the matrix) |
| 9 | Overlay + ESP | Click-through needs Win32 styles, not just Qt; DPI awareness; features return shapes, not drawings |
| 10 | Polish, game FOV | The game doesn't clamp FOV; restore what you change; PyQt5 aborts on slot exceptions; a second instance can wipe the first one's log |

The full story, with every bug and how it was tracked down, is in [`docs/DEVLOG.md`](docs/DEVLOG.md).

### Want to dig deeper?
- [`docs/DEVLOG.md`](docs/DEVLOG.md): the dated build diary.
- [`CLAUDE.md`](CLAUDE.md): architecture, data flow, the full offset table, a long list of gotchas and the decision log.
- [`src/actrainer/offsets.py`](src/actrainer/offsets.py): every address, with a comment saying what it is.
- The `tools/` scripts: run them with the game open to watch each piece work on its own.
- The [AssaultCube source](https://github.com/assaultcube/AC) (tag `v1.3.0.2`): `playerent`, `vecfromyawpitch()` and
  `transplayer()` explain most of the numbers above.
- Next step: [**Internal Cheat**](https://github.com/BigH018/internal-assault-cube), the same trainer as a C++ DLL inside
  the game, with function calls, hooks, code caves and chams.

## Credits and licences
- **Logo:** chibi fan art of Gojo (*Jujutsu Kaisen*) by the artist **Miraikitsu** (their watermark is on the image), used
  for this personal project. All rights to the artwork belong to the artist.
- **[AssaultCube](https://assault.cubers.net/)** by Rabid Viper Productions and the AssaultCube team (zlib licence).
- **[pymem](https://github.com/srounet/Pymem)** (MIT), **[PyQt5](https://www.riverbankcomputing.com/software/pyqt/)** by
  Riverbank Computing (GPL v3) and **[pytest](https://pytest.org)** (MIT).
- This project's own code is under the [MIT licence](LICENSE).
