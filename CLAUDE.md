# CLAUDE.md — AssaultCube Learning Trainer

This file is the project's memory. A fresh session must be able to work from this file alone.
**Keep it accurate.** See the Maintenance Rule at the bottom.

---

## 1. Project purpose and hard limits

A personal **learning project**: an external trainer for **AssaultCube 1.3.0.2 (Lockdown Edition)**,
written in Python. It has a PyQt5 menu, a customisable aimbot, an ESP overlay, player value editing
and a keybind system.

AssaultCube is a free, open-source FPS that runs offline against bots and has no anti-cheat. That makes
it the standard beginner target for learning about process memory, pointer chains, vector maths,
world-to-screen projection and building a real desktop app with a settings menu and overlay.

### Hard limits (never violate, never "just this once")
- **Offline bot matches only.** No features meant for online or multiplayer use.
- **No anti-cheat bypasses, no stealth or detection evasion, no code injection, no DLLs.**
  External memory reading and writing only, through `pymem`.
- **No obfuscation, packing, licensing, or anything aimed at distributing or selling this.**
- **No network code of any kind.** No sockets, HTTP, telemetry or update checks.

If a task would need any of the above, stop and tell the user instead.

---

## 2. Session start protocol

1. Read this whole file.
2. Check **§13 Current Status** to see which phase is in progress and what comes next.
3. Confirm your understanding to the user in 2–3 lines (where we are, what the task is).
4. Plan before coding: list the files you'll touch and why. Ask if anything is unclear. Don't guess.
5. After the task, follow the **Maintenance Rule** (§15).

### Phase workflow
At the end of each build phase:
1. Summarise what changed.
2. Tell the user exactly what to do in-game to test it, and what they should see.
3. Update this file and `docs/DEVLOG.md`.
4. **Stop and wait for the user's OK.** Only after approval, commit with a clear, focused message.
   **Commits must not include any Claude/AI co-author or "Generated with" lines.** The user is the sole author.

---

## 3. Tech stack, install, run, test

| What | Choice |
|---|---|
| Language | Python 3.11+ (user has 3.11.9, 64-bit, at `C:\Program Files\Python311`) |
| OS | Windows only |
| Memory | `pymem` (imported only in `memory/`) |
| UI and overlay | `PyQt5` |
| Win32 | `ctypes` (only in `winapi/`) |
| Tests | `pytest` |
| Settings | JSON profiles in `profiles/` |

Don't add extra packages without asking the user first.

```powershell
# install (from the project root)
python -m pip install -r requirements.txt
python -m pip install -e .          # editable install so `actrainer` is importable everywhere

# run the trainer (start AssaultCube first, windowed or borderless)
python -m actrainer

# run the debug scripts (one per phase)
python tools\phase1_local_player.py

# tests
python -m pytest
```

Notes:
- 64-bit Python can read the 32-bit `ac_client.exe` fine. Pointers must still be read as **uint32**.
- If the game runs as admin, the trainer must also run as admin. Otherwise `OpenProcess` fails.

---

## 4. File tree

Status markers: ✅ exists, 🔲 planned (phase number in brackets).

```
assault cube project/
  CLAUDE.md                     ✅ this file: project memory and rules
  README.md                     ✅ short overview, install/run, limits
  requirements.txt              ✅ pinned-minimum dependencies
  .gitignore                    ✅ Python + local profiles/logs
  pyproject.toml                ✅ package metadata (src layout, editable install) + pytest config (importlib mode, pythonpath=tests)
  docs/
    DEVLOG.md                   ✅ dated log of what was built, decisions and bugs fixed
  profiles/
    default.json                🔲 [4] committed default profile (all other profiles are git-ignored)
  tools/
    phase1_local_player.py      ✅ live print of local player position/angles/health/team (auto-reattach)
    phase1_dead_diag.py         ✅ F9 snapshots (alive/dead/alive) of the player struct; prints changed offsets + camera vs player ptr
    phase2_entities.py          ✅ live table of every bot (name/hp/armor/team/head/distance/state) + raw slot list
    phase3_angles_check.py      ✅ read-only: your view angles vs calc_aim_angles for the bot nearest your crosshair
    phase8_view_matrix.py       🔲 [8] prints one bot's screen coords to verify world_to_screen
  tests/
    helpers/__init__.py         ✅ makes shared helpers importable (pytest pythonpath = tests)
    helpers/gl_matrix.py        ✅ pure-Python GL matrix maths + ac_view_projection() that mimics AC's transplayer()
    helpers/fake_game.py        ✅ make_player_buffer() + FakeProcess (dict-backed memory) for game-layer tests
    game/test_player.py         ✅ player struct parsing + local/bot validity checks
    game/test_entities.py       ✅ entity list: null/local/dead/garbage/unreadable skipping, bad count, uint32 pointers
    maths/test_vectors.py       ✅ vector helper tests
    maths/test_angles.py        ✅ aim angles (cardinal dirs, +90 offset, round trip), normalisation, shortest-path smoothing, FOV
    maths/test_projection.py    ✅ world_to_screen: column-major, y flip, behind-camera, AC-engine matrix centre/up/right tests, FOV circle
    maths/test_skeleton.py      ✅ skeleton heights, symmetry, perpendicular to facing, crouch scaling, bones
    settings/test_store.py      🔲 [4] profile round-trip, defaults, schema migration
    input/test_keybinds.py      🔲 [4] hold/toggle/press-once state machine, conflicts
    features/test_aimbot.py     🔲 [6] target selection + priority + filters
    features/test_player_values.py 🔲 [7] set-now/freeze logic and value validation
    features/test_esp.py        🔲 [9] draw-primitive generation
  src/actrainer/
    __init__.py                 ✅ package marker, __version__
    __main__.py                 🔲 [5] lets `python -m actrainer` call main.main()
    main.py                     🔲 [5] entry point: DPI awareness, QApplication, load profile, wire services, start tick
    config.py                   ✅ non-offset constants: process name, pointer/world/health sanity limits (caps, rates, paths added later)
    offsets.py                  ✅ ALL offsets + GAME_VERSION + PLAYER_READ_SIZE: single source of truth
    app/
      controller.py             🔲 [6] QTimer tick: keybinds -> GameState -> aimbot -> values -> ESP -> overlay
    settings/
      models.py                 🔲 [4] dataclasses for all settings (pure)
      store.py                  🔲 [4] load/save/list/rename/delete profiles, defaults, schema migration
      signals.py                🔲 [5] Qt signal hub so UI changes apply live
    memory/
      __init__.py               ✅ package marker (only package allowed to import pymem)
      process.py                ✅ GameProcess: attach/detach/is_alive, module base, typed u32/i32/f32 read/write; AttachError/MemoryAccessError
    game/
      __init__.py               ✅ package marker
      structs.py                ✅ Vec3, PlayerSnapshot, GameState (frozen, pure data)
      player.py                 ✅ one-read player struct parsing (parse_player is pure) + local/bot validity checks
      local_player.py           ✅ [1] read local player; 🔲 [6] write view angles; 🔲 [7] write player values
      entities.py               ✅ read_player_count / read_entity_pointers (one read) / read_entities -> list[PlayerSnapshot]
      view.py                   🔲 [8] read view matrix + game FOV
      state.py                  🔲 [6] read_game_state(): one call that builds a full GameState per tick
    maths/
      __init__.py               ✅ package marker
      vectors.py                ✅ add/sub/scale/dot/cross/length/length_2d/distance/normalize/lerp, UP
      angles.py                 ✅ Angles; calc_aim_angles, direction_from_angles, normalize_yaw, clamp_pitch, yaw_delta, angular_distance, is_within_fov, smooth_angles
      projection.py             ✅ world_to_screen (column-major, rejects w<0.001, y flipped), fov_circle_radius
      skeleton.py               ✅ JOINTS proportions, BONES, facing_vectors, build_skeleton -> Skeleton
    features/
      primitives.py             🔲 [9] pure draw-primitive dataclasses (Line, Rect, Circle, Text)
      aimbot.py                 🔲 [6] target selection + smoothed aiming (no Qt)
      esp.py                    🔲 [9] settings + GameState -> list of draw primitives (no Qt)
      player_values.py          🔲 [7] set-now and freeze logic
    input/
      keys.py                   🔲 [4] key names <-> virtual-key codes, mouse buttons
      keybinds.py               🔲 [4] action registry, hold/toggle/press-once state machine, conflicts
    ui/
      theme.py                  🔲 [5] dark stylesheet, colours, fonts
      menu_window.py            🔲 [5] main window with tabs and status bar
      tabs/
        aimbot_tab.py           🔲 [5]
        esp_tab.py              🔲 [5]
        player_tab.py           🔲 [5]
        keybinds_tab.py         🔲 [5]
        settings_tab.py         🔲 [5]
      widgets/
        keybind_button.py       🔲 [5] "press a key to bind" button (polls key states)
        colour_button.py        🔲 [5] colour picker button
        labelled_slider.py      🔲 [5] slider with label and live value
    overlay/
      window.py                 🔲 [9] transparent click-through window that tracks the game client rect
      painter.py                🔲 [9] draws a list of primitives with QPainter
    winapi/
      __init__.py               ✅ package marker (only package allowed to make ctypes Win32 calls)
      win32.py                  ✅ [1] is_key_down (GetAsyncKeyState); 🔲 [4+] ctypes: find window, client rect, foreground, DPI, key states, ex-styles, file version
```

---

## 5. Dependency rules and data flow

### One-way dependency rules
- **Pure modules** (no I/O, no pymem, no Qt, no ctypes): `maths/`, `game/structs.py`,
  `settings/models.py`, `features/primitives.py`, `config.py`, `offsets.py`. All fully unit-testable.
- `pymem` is imported **only** in `memory/`.
- `PyQt5` is imported **only** in `ui/`, `overlay/`, `settings/signals.py`, `app/` and `main.py`.
- `ctypes` Win32 calls happen **only** in `winapi/`.
- `features/` depend on `game/structs.py`, `maths/` and `settings/models.py`. They **never** import
  `ui/`, `overlay/`, `memory/` or Qt. Features receive data and return decisions. The controller performs the I/O.
- **The UI never touches memory.** It only edits settings. The controller reads settings every tick.
- **No hardcoded offsets anywhere except `offsets.py`.**
- Each tab is its own file. Shared controls go in `ui/widgets/`.

### Data flow
```
            ┌──────────── settings (models.Settings, one shared instance) ◄──── UI tabs (edit only)
            │                                │
            ▼                                ▼
memory/process ─► game/(local_player, entities, view, state) ─► GameState ─► features/aimbot ──► write angles (via game/local_player)
                                                                    │──────► features/player_values ► write values (via game/local_player)
                                                                    └──────► features/esp ─► [primitives] ─► overlay/painter
input/keybinds (polls winapi key states) ─► action states ─► controller enables/disables features
```

### Tick loop (`app/controller.py`)
A `QTimer` fires at `settings.general.tick_rate_hz` (default 60 Hz). Each tick:
1. **Poll keybinds**: `winapi` key states → `input/keybinds` state machine → active actions.
   Skipped while the menu is capturing a new bind.
2. **Ensure attached**: if not attached, try to reattach (throttled, e.g. once per second), update status, end the tick.
3. **Read GameState** with `game/state.read_game_state()` (local player, entities, view matrix, FOV).
4. **Aimbot**: `features/aimbot` picks a target and returns new angles → controller writes them.
5. **Player values**: `features/player_values` returns writes (set-now requests + freezes) → controller writes them.
6. **ESP**: `features/esp` returns draw primitives → `overlay.set_primitives(...)` → `update()` (repaint).
7. **Status**: emit attached/entity count/tick rate to the menu (throttled).

Keep each tick fast. **On a read error: log it, skip the tick, never crash.** If the process is gone, detach and go back to step 2.

---

## 6. Offsets summary (`src/actrainer/offsets.py`)

All offsets live in `offsets.py` with `GAME_VERSION = "1.3.0.2"`. Module: `ac_client.exe` (32-bit).

### Offset change rule
You may change an offset yourself when you suspect it is wrong, **only if** you:
1. **Prove it first** with a diagnostic, memory scan or test showing the old value is wrong and the new one is right.
   If the proof needs the user in-game, write the diagnostic and ask them to run it.
2. **Keep the old value as a comment** next to the new one in `offsets.py`.
3. **Record** old value, new value, evidence and reason in the Decision log (§14) and `docs/DEVLOG.md`.
4. **Flag it** at the very top of the phase summary as **"OFFSET CHANGED"**.

**Never change an offset based on a guess alone.**

| Static (module base +) | Offset | Kind |
|---|---|---|
| Local player (`player1`) | `0x18AC00` | **pointer** → player address (stays valid while dead) |
| Camera (`camera1`) | `0x17E0A8` | **pointer**: equals player1 while alive, death-cam object while dead. **Not** for player reads |
| Entity list | `0x18AC04` | **pointer** → array of 4-byte entity pointers |
| Player count | `0x18AC0C` | int (includes local player) |
| View FOV | `0x18A7CC` | float |
| View matrix | `0x17DFD0` | 16 floats **stored in place** (NOT a pointer) |

| Player struct field | Offset | Type |
|---|---|---|
| headPos | `0x04` | Vec3 floats (z is up) |
| feetPos | `0x28` | Vec3 floats |
| viewHeading (yaw) | `0x34` | float, 0–360 |
| viewPitch | `0x38` | float, -90..90 |
| health | `0xEC` | int |
| armor | `0xF0` | int |
| reserve ammo | pistol `0x108`, carbine `0x10C`, shotgun `0x110`, SMG `0x114`, sniper `0x118`, assault `0x11C` | int |
| magazine ammo | pistol `0x12C`, carbine `0x130`, shotgun `0x134`, SMG `0x138`, sniper `0x13C`, assault `0x140` | int |
| grenades | `0x144` | int |
| akimbo ammo | `0x148` | int |
| name | `0x205` | char[16] |
| team | `0x30C` | int |
| dead | `0x318` | int |

Entity list: slot 0 is often null or the local player. Skip null pointers, the local player, dead
entities and invalid data without crashing.

### Validity checks (important)
- **Local player:** valid = non-null pointer in a sane user-space range **and** a finite position within
  `config.WORLD_COORD_LIMIT`. **Never use health 0–100 for the local player.** The Player tab can set
  health to e.g. 999, and the trainer would then think the local player is invalid. Health only gets a very
  wide sanity range (`config.LOCAL_HEALTH_SANE_*`).
- **Bots:** same pointer + position checks, plus a loose health filter to reject garbage entries:
  alive → `BOT_HEALTH_MIN..MAX` (0–100); dead → `BOT_DEAD_HEALTH_MIN..MAX` (health goes negative on death).
- **Entity list:** count clamped to `config.MAX_ENTITIES`; the pointer array is read in one call; one bad entity is
  logged at DEBUG and skipped, never fatal. `read_entities(..., include_dead=False)` skips dead bots by default.

---

## 7. Settings system

- `settings/models.py`: one root `Settings` dataclass made of `GeneralSettings`, `AimbotSettings`,
  `EspSettings`, `PlayerSettings` (a dict of `value_id -> ValueSetting(target, freeze)`) and
  `KeybindSettings` (a dict of `action_id -> Bind(key, mode)`). Colours are stored as `"#RRGGBBAA"`
  strings so the models stay Qt-free.
- **One shared `Settings` instance** is created in `main.py`. UI tabs mutate it directly and then emit a
  signal from `settings/signals.py`. The controller reads it each tick, so changes apply live with no restart.
  Signals exist only for things that must *react* (e.g. tick rate → timer interval, overlay visibility).
- **Explicit save only.** Changes apply live but are not written to disk until the user clicks Save.
  Unsaved changes show a marker (`*` in the window title + "Unsaved changes" label in the Settings tab).
  Any `settings_changed` signal sets the dirty flag. Save, load and reset clear it.
- `settings/store.py`: profiles are `profiles/<name>.json`. The last used profile name is kept in
  `profiles/.last_profile` (git-ignored) and auto-loaded on startup. `profiles/default.json` is committed.
- **Versioning:** each profile has `"schema_version": N`. `store.py` holds `CURRENT_SCHEMA_VERSION` and an
  ordered list of `migrate_vN_to_vN+1(dict) -> dict` functions applied on load. Unknown keys are ignored
  (and logged). Missing keys fall back to dataclass defaults. Out-of-range values are clamped.

### Adding a new setting end-to-end
1. **Model:** add a typed field with a default to the right dataclass in `settings/models.py`.
   Put min/max/step constants in `config.py`.
2. **Default/version:** if old profiles need a value other than the default, bump
   `CURRENT_SCHEMA_VERSION` and add a migration. Update `profiles/default.json`.
3. **UI control:** add the widget in the relevant `ui/tabs/*_tab.py`, initialise it from settings,
   write back on change, emit `settings_changed`. Also refresh it in the tab's `load_from_settings()` (called after a profile load).
4. **Feature:** read the field in the feature module (`features/*.py`) and add a unit test.
5. Update this file (§7 if the pattern changed, §13 status).

---

## 8. Keybind system (`input/keys.py`, `input/keybinds.py`)

- Keys are stored as **virtual-key codes** (ints) and shown as names via `keys.py`.
  Supported mouse buttons: LMB, RMB, MMB, Mouse4 (X1), Mouse5 (X2). The scroll wheel **can't** be polled with `GetAsyncKeyState`.
- **Modes:** `HOLD` (active while held), `TOGGLE` (flips on each press), `PRESS` (fires once on the press edge).
  Each action declares which modes it allows and a default.
- The state machine is pure: `update(pressed_vks: set[int]) -> ActionStates`. It's fed by
  `winapi.get_pressed_keys()`, which makes it testable without Windows.
- **Registering a new action:**
  1. Add an `ActionDef(id, label, category, allowed_modes, default_mode, default_key)` to the registry in `keybinds.py`.
  2. Add its default bind to `KeybindSettings` defaults (and `profiles/default.json`).
  3. Handle the action in `app/controller.py` (read its state each tick).
  4. The Keybinds tab lists the registry automatically, so no UI work is needed.
- **Conflicts:** `find_conflicts(binds) -> list[(key, [action_ids])]`. The Keybinds tab highlights them.
- Default binds: menu toggle `INSERT` (PRESS), panic `END` (PRESS), quit unbound, aimbot RMB (HOLD).

---

## 9. Adding a menu tab or widget

- **Tab:** create `ui/tabs/<name>_tab.py` with a `QWidget` subclass that takes `(settings, signals)`,
  builds its controls, and implements `load_from_settings()`. Register it in `ui/menu_window.py`'s tab list.
- **Widget:** if a control is used in more than one tab (or is non-trivial), put it in `ui/widgets/`.
  Widgets expose a Qt signal like `valueChanged`. They never know about `Settings`.
- All styling goes through `ui/theme.py`. No inline colours in tabs.

### Menu window behaviour
- **Menu toggle** (default `INSERT`, PRESS, rebindable) shows/hides the menu. It's polled in the tick, so it works while the game is focused.
- **Shown:** always-on-top, raised and activated. Centred over the game window the **first** time.
  After that it remembers its position (stored in `GeneralSettings.menu_pos`).
- **Hidden:** fully hidden (not minimised). Focus goes back to the game window.
- **Mouse capture plan (to be verified in Phase 5):** AssaultCube grabs the mouse while playing. On show we
  bring the menu to the foreground. Windows' foreground lock normally blocks this for a background process, so
  `winapi` uses `AttachThreadInput` to the current foreground thread + `SetForegroundWindow` + `BringWindowToTop`.
  When the game loses focus it should release the cursor. If that turns out to be unreliable, the
  fallback is documented: press `Esc` in-game first to free the cursor. The findings go in §10.
- **Close (X) button:** asks "Quit trainer / Hide menu / Cancel". A **Quit** button in the menu exits cleanly
  (unfreezes values, closes overlay). There's no default quit key.
- **Overlay stays visible** while the game **or** the menu has focus. It's hidden when anything else is foreground or the game isn't running.

---

## 10. Known gotchas

- **32-bit pointers:** read pointers as 4-byte `uint32`. Reading 8 bytes breaks every pointer chain.
- **Pointers vs direct values:** local player and entity list are *dereferenced*. The view matrix is read *in place*.
- **Yaw convention:** AC yaw is offset by 90° from standard `atan2` maths, and angles are in degrees.
  From the game's `vecfromyawpitch()`: forward = (sin yaw·cos pitch, −cos yaw·cos pitch, sin pitch), so yaw 0 faces −y,
  90 faces +x, and `yaw = atan2(dx, −dy)` = `atan2(dy, dx) + 90°`. Pitch = `atan2(dz, horizontal dist)`, + is up.
  Normalise yaw to 0–360, clamp pitch to -90..90.
  **Smooth along the shortest yaw direction** (no spinning the long way round past 0/360).
- **View matrix is OpenGL column-major.** `clip.x = m[0]*x + m[4]*y + m[8]*z + m[12]` (etc.).
  Reject points behind the camera (`w < 0.001`). NDC → pixels with **y flipped**.
- **Overlay:** frameless, translucent, always-on-top, click-through (`WA_TransparentForMouseEvents` plus
  `WS_EX_LAYERED | WS_EX_TRANSPARENT`), sized to the game's **client** area (not the window frame).
  The process **must be DPI-aware** (set before `QApplication` is created) or drawings will be offset on scaled displays.
- **Global hotkeys:** poll `GetAsyncKeyState` in the tick so they work while the game is focused.
  Ignore keybinds while the menu is capturing a new bind.
- **Bind capture and LMB:** clicking the bind button is itself a left click. Capture must wait until all
  keys are released before accepting a press, or every bind becomes LMB.
- **Value writes and freezes** only run when attached and in a match (local player pointer valid, sane position).
  Validate: no negatives, caps in `config.py`.
- **Don't validate the local player with health 0–100:** the trainer itself can set health above 100 (see §6 Validity checks).
- **The game must run windowed or borderless** for the overlay to sit on top.
- **Lifecycle:** the game may be missing, close mid-session, or be between matches. Show status, keep the menu usable,
  auto-reattach.
- **Camera pointer ≠ local player:** `0x17E0A8` (camera1) points at the player only while alive. On death it
  switches to a static death-cam object (e.g. `0x00595410`, a different class). Reading player fields through it
  gives an empty name, `dead = 0` and ASCII file paths where ammo should be. Always use `LOCAL_PLAYER_PTR` (`0x18AC00`).
- **AC's world is LEFT-handed** (renderer: "Z-up LH quake style"). The player's screen-right is `up × forward`;
  `forward × up` points LEFT. Caught by `test_up_is_up_and_right_is_right`.
- **Smoothing depends on tick rate:** each tick moves 1/smoothing of the remaining angle, so a higher tick rate aims faster.
- **FOV circle assumes the game FOV is horizontal** (AC derives fovy from fov and aspect). Confirm in Phase 9.
- **Health goes negative on death** (e.g. -54). Use `dead` (`0x318`) for alive/dead, never `health > 0`.
- **Finding offsets by diffing:** take struct snapshots in state A / B / A again (`tools/phase1_dead_diag.py`).
  Values equal in both A snapshots but different in B are "STRONG" candidates. This filters out timers and movement noise.
- **Finding static pointers:** to check which static slots hold an address, scan the module image
  (base + 0x100000..0x1A0000) for the 4-byte little-endian value. Neighbouring values (capacity/count) often reveal
  the source-level layout.
- **pymem log noise:** pymem installs its own DEBUG handler on import. `memory/process.py` sets the `pymem` logger to WARNING.
- **Default player name** in AC is `unarmed`. Seeing that name means the read works.
- **Team check in free-for-all modes (confirmed Phase 2):** in FFA deathmatch, bots still have team 0/1 and some share
  the local player's team. Team check would wrongly skip them, so it must stay a user toggle (off for FFA).
  There's no game-mode offset yet.

---

## 11. Coding conventions

- Type hints everywhere. `from __future__ import annotations` at the top of modules.
- Dataclasses for data. Frozen dataclasses for snapshots (`Vec3`, `PlayerSnapshot`, `GameState`).
- Small functions. Docstrings on every public function/class.
- `logging` only (`log = logging.getLogger(__name__)`). **No `print` in library code.** `tools/` scripts may print.
- No magic numbers. User-tunable/project constants go in `config.py`, offsets in `offsets.py`. Fixed maths/domain
  constants (e.g. skeleton proportions, `MIN_CLIP_W`) live as named module-level constants next to the maths that uses them.
- Brief comments explaining the **why** behind maths and memory code (the user is learning).
- Simple, readable code over clever code.
- Tests mirror the source layout under `tests/`.

---

## 12. Do's and don'ts

**Do**
- Respect the hard limits in §1.
- Keep features Qt-free and memory-free so they're testable.
- Handle errors at the controller boundary: log, skip the tick, recover.
- Ask the user when something is unclear.
- Keep commits small and focused. Commit only after the user approves a phase.

**Don't**
- Don't add packages without asking.
- Don't import pymem, Qt or ctypes outside their allowed folders.
- Don't hardcode offsets outside `offsets.py`. Don't change `offsets.py` values without following the
  Offset change rule (§6): proof, old value in a comment, decision log + DEVLOG, "OFFSET CHANGED" flag.
- Don't use `print` in library code.
- Don't let the UI read or write memory.
- Don't add network code, injection, evasion, obfuscation or distribution features.
- Don't add Claude/AI co-author or attribution lines to commits or PRs.

---

## 13. Current Status

- [x] **Step 0:** CLAUDE.md, README, requirements, .gitignore, plan. *(approved 2026-10-03)*
- [x] Phase 1: Memory: attach, read local player, live debug print *(done 2026-10-03: local player pointer corrected to 0x18AC00; dead flag 0x318 verified)*
- [x] Phase 2: Entities: print every bot *(built + verified against running game: 7 bots read; awaiting user test)*
- [x] Phase 3: Maths: angles, projection, skeleton + tests *(107 tests passing; awaiting in-game angle check)*
- [ ] Phase 4: Settings + keybinds core + tests
- [ ] Phase 5: Menu shell (all tabs wired to settings, profiles, menu hotkey)
- [ ] Phase 6: Controller + aimbot
- [ ] Phase 7: Player values (set-now, freeze, keybinds)
- [ ] Phase 8: View matrix debug script
- [ ] Phase 9: Overlay + ESP + FOV circle
- [ ] Phase 10: Polish (panic, reattach, status, conflicts, error handling, docs)

**Next:** user runs phase3_angles_check → commit → Phase 4 (settings + keybinds core).

---

## 14. Decision log

- **2026-10-03:** `platform/` renamed to `winapi/`. A package called `platform` shadows the stdlib
  `platform` module whenever its parent folder lands on `sys.path` (e.g. running a file directly), which breaks
  libraries that import it.
- **2026-10-03:** Added `config.py` for non-offset constants (caps, defaults, paths) so `offsets.py` holds only offsets.
- **2026-10-03:** Added `game/state.py` so the controller makes one call per tick to get a full `GameState`.
- **2026-10-03:** Added `features/primitives.py`: ESP outputs pure draw primitives, and the overlay only knows
  how to paint primitives. This keeps ESP testable and Qt-free.
- **2026-10-03:** Aimbot FOV is measured in **degrees** (angular distance from the crosshair). That makes it
  resolution-independent. The FOV circle radius in pixels is derived from it using the game's view FOV.
- **2026-10-03:** Smoothing: each tick, move `1/smoothing` of the remaining (shortest-path) angle delta.
  1 = instant snap.
- **2026-10-03:** Key capture polls `GetAsyncKeyState` (not Qt key events). That way keyboard and mouse
  buttons are captured the same way, matching how binds are detected at runtime.
- **2026-10-03:** Panic (END) disables aimbot and ESP and unfreezes all values. Quit is a separate, unbound action,
  plus a Quit button. Closing the window asks quit/hide.
- **2026-10-03:** Profiles use explicit Save with an unsaved-changes marker (user preference).
- **2026-10-03:** Overlay is visible while the game or the menu is focused, so ESP changes can be seen while tweaking.
- **2026-10-03:** Local player validity uses pointer + position, never health 0–100 (the trainer can set health > 100).
- **2026-10-03:** Added `game/player.py`: player parsing + validity checks are shared by local player and entities.
  Each struct is read in ONE call (`PLAYER_READ_SIZE`) and unpacked locally with explicit `struct` formats.
- **2026-10-03:** **Offset change:** `LOCAL_PLAYER_PTR` `0x17E0A8` → `0x18AC00`. The original value is `camera1`,
  which switches to a death-cam object on death (the pointer changed 0x009DD2C8 → 0x00595410 in the diagnostic).
  `0x18AC00` is `player1`, declared right before the `players` vector (0x18AC04 buf / 0x08 capacity / 0x0C count).
  Old value kept as `CAMERA_PTR`. Verified across a death: player1 stayed 0x009DD2C8, camera switched to 0x00595410 and back.
- **2026-10-03:** `DEAD` at `0x318` verified correct (0 → 1 → 0 across a death). It only *looked* broken because of the
  camera pointer. A byte at `0x76` also flips 0 → 1 (likely the `state` enum, CS_ALIVE = 0 / CS_DEAD = 1). It's a backup
  candidate, not in `offsets.py`. Health goes negative on death (-54 observed).
- **2026-10-03:** `winapi/win32.py` started early (only `is_key_down`) for the dead-flag diagnostic. The rest comes in Phase 4.
- **2026-10-03:** pytest uses `--import-mode=importlib` so test folders don't need `__init__.py`.
- **2026-10-03:** Offset change rule added (§6): offsets may be changed only with proof, old value kept in a comment,
  logged in decision log + DEVLOG, and flagged "OFFSET CHANGED" in the phase summary.
- **2026-10-03:** Dead bots use a wider health lower bound (`BOT_DEAD_HEALTH_MIN`), since health goes negative on death.
  Otherwise dead bots would be rejected as garbage.
- **2026-10-03:** Yaw formula derived from AC's `vecfromyawpitch()` and cross-checked by building the view matrix
  exactly like AC's `transplayer()` in tests (`helpers/gl_matrix.py`). A point along `direction_from_angles` projects to
  screen centre at 7 yaw/pitch combos.
- **2026-10-03:** FOV distance uses the true angle between direction vectors (acos of dot), not hypot(yaw diff, pitch diff),
  so it stays correct when looking steeply up or down.
- **2026-10-03:** Skeleton right vector is `up × forward` (AC world is left-handed). The first version used `forward × up`
  and the projection test showed it landing screen-left.
- **2026-10-03:** Shared test fakes live in `tests/helpers/` (pytest `pythonpath = ["tests"]`). `FakeProcess` is
  duck-typed (read_bytes / read_u32 / read_i32 / module_base), so game-layer code is tested without the game.
- **2026-10-03:** src layout (`src/actrainer`) + `pyproject.toml` editable install, so tools, tests and
  `python -m actrainer` all import the package the same way.

---

## 15. Maintenance rule

**After EVERY task**, before finishing:
1. Update the **file tree** (§4): status markers, new/removed files, one-line descriptions.
2. Update **Current Status** (§13) and the **Next** line.
3. Update any rules, gotchas or patterns that changed (§5–§12), and add to the **Decision log** (§14).
4. Add a dated entry to `docs/DEVLOG.md`.
