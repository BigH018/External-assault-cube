# CLAUDE.md — AssaultCube Learning Trainer

This file is the project's memory. A fresh session must be able to work from this file alone.
**Keep it accurate.** See the Maintenance Rule at the bottom.

---

## 1. Project purpose and hard limits

A personal **learning project**: an external trainer for **AssaultCube 1.3.0.2 (Lockdown Edition)**,
written in Python. It has a PyQt5 menu, a customisable aimbot, an ESP overlay, player value editing,
a game FOV changer and a keybind system. **All 10 build phases are complete (2026-10-03).**
Display name / branding: **W Cheat - By BigH** (the user's logo: `docs/assets/logo-source.jpg`, used via `ui/assets/logo.png`). The Python
package stays `actrainer`.

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

# run the trainer (start AssaultCube first, windowed or borderless). Logs: console + logs\actrainer.log
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
  README.md                     ✅ overview, install/run, full usage guide (menu, hotkeys, troubleshooting), limits
  requirements.txt              ✅ pinned-minimum dependencies
  .gitignore                    ✅ Python + local profiles/logs
  .gitattributes                ✅ LF line endings everywhere (no CRLF warnings)
  pyproject.toml                ✅ package metadata (src layout, editable install) + pytest config (importlib mode, pythonpath=tests)
  docs/
    DEVLOG.md                   ✅ dated log of what was built, decisions and bugs fixed
    assets/logo-source.jpg      ✅ the user's original 1920 px logo artwork (source for all logo PNGs)
    assets/logo.png             ✅ README banner logo (256 px, smooth downscale of the source)
    screenshots/                ✅ README screenshots: esp.jpg, esp-skeleton.jpg, menu-{aimbot,esp,player,keybinds,settings}.png,
                                   colour-picker.png (regenerate with tools/readme_shots_*.py after UI changes)
  profiles/
    default.json                ✅ committed default profile = code defaults (test-enforced; all other profiles are git-ignored)
  tools/
    phase1_local_player.py      ✅ live print of local player position/angles/health/team (auto-reattach)
    phase1_dead_diag.py         ✅ F9 snapshots (alive/dead/alive) of the player struct; prints changed offsets + camera vs player ptr
    phase2_entities.py          ✅ live table of every bot (name/hp/armor/team/head/distance/state) + raw slot list
    phase3_angles_check.py      ✅ read-only: your view angles vs calc_aim_angles for the bot nearest your crosshair
    phase4_keybinds.py          ✅ live keybind engine with real keys (HOLD/TOGGLE/PRESS incl. mouse buttons)
    phase8_view_matrix.py       ✅ read-only: centre check (own view dir -> screen centre), matrix-derived hfov, nearest bot head/feet on screen
    readme_shots_game.py        ✅ README images: grabs the game's client area + paints build_esp (2 variants) -> docs/screenshots/*.jpg
    readme_shots_menu.py        ✅ README images: renders every page + colour picker offscreen (showcase profile in a temp dir, live
                                   status from the game) -> docs/screenshots/*.png
  tests/
    conftest.py                 ✅ shared fixtures: offscreen QApplication (+ Windows fonts), settings, signals, tmp ProfileStore, ProfileSession
    helpers/__init__.py         ✅ makes shared helpers importable (pytest pythonpath = tests)
    helpers/gl_matrix.py        ✅ pure-Python GL matrix maths + ac_view_projection() that mimics AC's transplayer()
    helpers/fake_game.py        ✅ make_player_buffer(), FakeProcess (writable memory + attach/alive, records writes), make_fake_game() (+ matrix/fov)
    game/test_player.py         ✅ player struct parsing + local/bot validity checks
    game/test_state.py          ✅ read_game_state (local + live bots + matrix + fov, None without local), write_view_angles single write
    game/test_view.py           ✅ matrix read in place, FOV read, hfov recovered from AC-style + live matrices, sanity check
    game/test_entities.py       ✅ entity list: null/local/dead/garbage/unreadable skipping, bad count, uint32 pointers
    maths/test_vectors.py       ✅ vector helper tests
    maths/test_angles.py        ✅ aim angles (cardinal dirs, +90 offset, round trip), normalisation, shortest-path smoothing, FOV
    maths/test_projection.py    ✅ world_to_screen: column-major, y flip, behind-camera, AC-engine matrix centre/up/right tests, FOV circle
    maths/test_skeleton.py      ✅ skeleton heights, symmetry, perpendicular to facing, crouch scaling, bones
    settings/test_models.py     ✅ ranges, defaults within caps, weapons match offsets, unfreeze_all, replace_with
    settings/test_store.py      ✅ round-trip, forgiving load, clamping, keybind names/modes, migration, files, startup, default.json sync
    input/test_keys.py          ✅ name round-trip, unknown/unbound, Escape + generic modifiers not bindable
    input/test_keybinds.py      ✅ hold/toggle/press, suspension, reset, conflicts, action registry
    ui/test_binder.py           ✅ toggle/chip/segmented/slider/combo write settings + emit, reload after replace_with, keybind binder
    ui/test_profile_session.py  ✅ dirty flag, save/save as/load/rename/reset on the shared Settings
    ui/test_overlay.py          ✅ painter renders each primitive to the right pixels; window follows frames; repaint rate
    ui/test_menu_window.py      ✅ 5 pages + branding/logo, sidebar navigation, title marker, cross-page bind sync, conflict banner +
                                   sidebar badge, hotkey hint, refresh, status pill, FOV readout
    ui/test_widgets.py          ✅ toggle switch/row, segmented control, colour helpers, picker (presets keep opacity, slider, hex),
                                   colour chip live preview + cancel restores + apply keeps
    app/test_controller.py      ✅ hotkeys, capture suspension, attach throttling, status, tick rate; aimbot conditions + toggle;
                                   player values; overlay frames (game/menu focus, hide once, nothing to draw); game FOV set/keep/restore
    app/test_main.py            ✅ single-instance lock, unhandled exceptions logged instead of fatal
    features/test_aimbot.py     ✅ aim point, FOV/dead/team/distance filters, priorities + tie-break, snap/smooth, body lower, dead local, 0/360
    features/test_player_values.py ✅ field map, clamped targets, only-changed writes, freezes, no dup, dead = no writes, describe
    features/test_game_fov.py   ✅ set-now / keep-applied / already-applied / clamping
    features/test_esp.py        ✅ box geometry, behind/right, each style + combos, thickness, target, extras, health bar, snaplines,
                                   FFA vs team mode, draw order, FOV circle (incl. edge matches projection)
  src/actrainer/
    __init__.py                 ✅ package marker, __version__
    __main__.py                 ✅ lets `python -m actrainer` call main.main()
    main.py                     ✅ entry point: console logging + excepthook, DPI awareness, QApplication, single-instance lock, file
                                   logging, load profile (+ warnings dialog), wire signals/session/controller/menu/overlay, quit
    config.py                   ✅ non-offset constants: paths, logs, lock file, controller timing, branding (APP_NAME, APP_AUTHOR,
                                   MENU_TITLE, APP_USER_MODEL_ID), menu/sidebar/logo sizes, sanity limits,
                                   values/weapons + display names, ranges (incl. GAME_FOV_RANGE), caps
    offsets.py                  ✅ ALL offsets + GAME_VERSION + PLAYER_READ_SIZE: single source of truth
    app/
      __init__.py               ✅ package marker
      status.py                 ✅ ControllerStatus (pure): attached, pid, base, exe version, offsets_ok, entities, tick rate, focus,
                                   game_fov, player_values
      controller.py             ✅ QTimer tick: keybinds + actions, throttled attach + liveness, GameState read, aimbot (enabled+key+game focused)
                                   -> write angles, player values, game FOV (set/keep, restored on panic/quit), ESP -> OverlayFrame
                                   (visible while game or menu focused), notices, status; precise timer
    settings/
      __init__.py               ✅ package marker
      models.py                 ✅ Settings + sections (general/aimbot/esp/player/view/keybinds), enums, ranged() metadata, field_range, replace_with
      store.py                  ✅ to_dict/from_dict (forgiving, clamping, migrations) + ProfileStore (files, read-only default, last profile, startup)
      signals.py                ✅ AppSignals hub: settings_changed, refresh_requested, bind_capture_changed, set_value_requested,
                                   game_fov_set_requested, menu_toggle_requested, quit_requested, status_changed, notice, overlay_frame
    memory/
      __init__.py               ✅ package marker (only package allowed to import pymem)
      process.py                ✅ GameProcess: attach/detach/is_alive, module base, typed u32/i32/f32 read/write; AttachError/MemoryAccessError
    game/
      __init__.py               ✅ package marker
      structs.py                ✅ Vec3, PlayerSnapshot, GameState (frozen, pure data)
      player.py                 ✅ one-read player struct parsing (parse_player is pure) + local/bot validity checks
      local_player.py           ✅ read local player, write_view_angles (one 8-byte yaw+pitch write), editable field ids -> offsets
                                   (VALUE_FIELD_OFFSETS, mag_field/reserve_field), snapshot_value, write_player_value
      entities.py               ✅ read_player_count / read_entity_pointers (one read) / read_entities -> list[PlayerSnapshot]
      view.py                   ✅ read_view_matrix (16 floats in place), read_fov, write_fov, horizontal_fov_from_matrix, is_sane_matrix
      state.py                  ✅ read_game_state(): local player + live bots + view matrix + FOV (None outside a match)
    maths/
      __init__.py               ✅ package marker
      vectors.py                ✅ add/sub/scale/dot/cross/length/length_2d/distance/normalize/lerp, UP
      angles.py                 ✅ Angles; calc_aim_angles, direction_from_angles, normalize_yaw, clamp_pitch, yaw_delta, angular_distance, is_within_fov, smooth_angles
      projection.py             ✅ world_to_screen (column-major, rejects w<0.001, y flipped), fov_circle_radius
      skeleton.py               ✅ JOINTS proportions, BONES, facing_vectors, build_skeleton -> Skeleton
    features/
      __init__.py               ✅ package marker
      primitives.py             ✅ Line, Rect, FilledRect, Circle, Text (+TextAlign), OverlayFrame (pure)
      aimbot.py                 ✅ aim_point, find_candidates (filters), select_target (priority), compute_aim (smoothed angles + target)
      esp.py                    ✅ screen_box, styles (box/corner/head circle/skeleton), extras, team mode, FOV circle -> primitives (pure)
      player_values.py          ✅ ValueWrite, target_writes (clamped), frozen_ids, plan_writes (requested + frozen, only changed, none while dead), describe
      game_fov.py               ✅ target_fov (clamped), plan_fov_write (set-now / keep-applied, only when different)
    input/
      __init__.py               ✅ package marker
      keys.py                   ✅ VK <-> names, BINDABLE_VKS, mouse buttons
      actions.py                ✅ BindMode, Bind, ActionDef, ACTIONS registry (incl. View: set/keep game FOV), default_binds, set_/freeze_ ids
      keybinds.py               ✅ KeybindEngine (HOLD/TOGGLE/PRESS, suspended, reset_toggles), ActionStates, find_conflicts
    ui/
      __init__.py               ✅ package marker
      theme.py                  ✅ ice-blue palette, asset paths (logo), stylesheet (object names / dynamic properties), apply_theme
                                   (also sets the app icon), restyle
      assets/arrow_up.svg       ✅ spinbox arrow (stylesheet image)
      assets/arrow_down.svg     ✅ spinbox/combo arrow (stylesheet image)
      assets/logo.png           ✅ 256 px logo: window/taskbar icon + header logo (smoothly scaled)
      assets/logo.ico           ✅ the user's original 32 px icon (kept for shortcuts; not used by the app)
      binder.py                 ✅ SettingBinder (toggle/chip/segmented/slider/combo/colour <-> settings field), KeybindBinder
                                   (key button, mode combo, mode segmented), helpers
      layout.py                 ✅ group() (card), row(), labelled() (LABEL_WIDTH), hint()
      profile_session.py        ✅ ProfileSession: current profile, dirty flag, load/save/save as/rename/delete/reset
      menu_window.py            ✅ header (W Cheat · By BigH, status pill, logo top right) + sidebar nav (⚠ badge, hotkey hint, Quit,
                                   version) + stacked pages (title/subtitle + scroll); show/hide/foreground/placement; close prompt
      tabs/
        __init__.py             ✅ package marker
        aimbot_tab.py           ✅ TITLE/SUBTITLE; switches + segmented (key mode, target, priority), sliders, FOV circle colour chip
        esp_tab.py              ✅ TITLE/SUBTITLE; switches (enable, team mode, enemies only), style + info chips, colour chips, snapline segmented
        player_tab.py           ✅ TITLE/SUBTITLE; Game FOV card; stats + per-weapon mag/reserve: target, live "Now", Set now, key,
                                   Freeze switch; notice line
        keybinds_tab.py         ✅ TITLE/SUBTITLE; every action by category (from registry), mode, conflict highlight + banner
        settings_tab.py         ✅ TITLE/SUBTITLE; profiles, tick rate/overlay FPS, menu hotkey, reset, status panel
      widgets/
        __init__.py             ✅ package marker
        keybind_button.py       ✅ "press a key to bind" button (polls key states, waits for release, Esc clears, 6 s timeout)
        colour_button.py        ✅ colour chip (checkerboard swatch + "#RRGGBB · 100%"); opens the picker; live preview, cancel restores
        colour_picker.py        ✅ ColourPopup: presets, saturation/value square, hue bar, opacity %, hex, old/new previews;
                                   to_qcolor/from_qcolor/parse_hex/describe/paint_checker
        toggle_switch.py        ✅ animated ToggleSwitch (checkable QAbstractButton) + ToggleRow (label/description + switch)
        segmented.py            ✅ SegmentedControl: joined exclusive buttons for one-of-N choices
        labelled_slider.py      ✅ slider with label (LABEL_MIN_WIDTH = 120) and live value (float via decimal scaling)
    overlay/
      __init__.py               ✅ package marker
      window.py                 ✅ OverlayWindow: frameless/topmost/translucent/click-through, follows OverlayFrame rect, repaint at overlay_fps (precise timer)
      painter.py                ✅ paint(QPainter, primitives): antialiased shapes, shadowed text, cached colours
    winapi/
      __init__.py               ✅ package marker (only package allowed to make ctypes Win32 calls)
      win32.py                  ✅ key state, set_dpi_aware, find_main_window, client/window rects, is_minimized, force_foreground,
                                   make_click_through (WS_EX_LAYERED|TRANSPARENT|TOOLWINDOW|NOACTIVATE), set_app_user_model_id,
                                   process image path, file version
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
                                                                    │──────► features/game_fov ──────► write FOV (via game/view)
                                                                    └──────► features/esp ─► [primitives] ─► overlay/painter
input/keybinds (polls winapi key states) ─► action states ─► controller enables/disables features
```

### Tick loop (`app/controller.py`)
A `QTimer` fires at `settings.general.tick_rate_hz` (default 60 Hz). Each tick:
1. **Poll keybinds**: `winapi` key states → `input/keybinds` state machine → active actions.
   Skipped while the menu is capturing a new bind.
2. **Ensure attached**: if not attached, try to reattach (throttled, e.g. once per second), update status, end the tick.
3. **Read GameState** with `game/state.read_game_state()` (local player, entities, view matrix, FOV).
4. **Aimbot**: only if `aimbot.enabled` AND the `aimbot` bind is active (HOLD held / TOGGLE on) AND the **game window is
   focused** (holding RMB over the menu never aims). `features/aimbot.compute_aim` picks a target and returns smoothed angles,
   then the controller writes them with `write_view_angles`. `controller.aim_target_address` remembers the target (ESP draws it thicker).
5. **Player values**: "Set now" (button or hotkey) emits `set_value_requested(id)`, and the controller queues it. Each tick
   `features/player_values.plan_writes(local, settings.player, queued)` returns writes for queued + frozen values, only for fields
   that differ and never while dead. The controller writes them (`write_player_value`) and emits a `notice`. Queued requests that
   can't run (not attached / not in a match) are dropped with a notice.
   **Game FOV**: `features/game_fov.plan_fov_write(state.fov, settings.view, requested)` → `write_fov`. The FOV before our first
   write is remembered and restored on panic and on quit.
6. **ESP / overlay**: `features/esp.build_esp(state, esp, aimbot, w, h, aim_target)` returns primitives (players + FOV circle).
   The controller wraps them with the game's client rect in an `OverlayFrame` and emits `overlay_frame`. The frame is visible
   only when there's something to draw AND the game or one of our windows (`QApplication.activeWindow()`) is focused. "Hidden"
   is emitted once, not every tick. `OverlayWindow` follows the rect and repaints at `overlay_fps` (independent of tick rate).
7. **Status**: emit `ControllerStatus` (attached, entities, tick rate, focus, game FOV, live player values) to the menu at 2 Hz.

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

- **`settings/models.py`** (pure): root `Settings` = `GeneralSettings` (tick rate, overlay FPS, `menu_pos`),
  `AimbotSettings`, `EspSettings`, `PlayerSettings` (`values: {stat -> ValueSetting(target, freeze)}` for
  `config.STAT_VALUES`, `ammo: {weapon -> AmmoSetting(mag, reserve, freeze)}` for `config.WEAPONS`),
  `ViewSettings` (game `fov` + `freeze` = keep applied) and `KeybindSettings` (`binds: {action_id -> Bind(key, mode)}`, defaults from the action registry).
  Enums: `AimTarget`, `TargetPriority`, `SnaplineOrigin`. Colours are `"#RRGGBBAA"` strings, so models stay Qt-free.
- **Ranges live in field metadata:** `fov_deg: float = ranged(15.0, config.AIM_FOV_RANGE)`. `field_range(cls, name)`
  returns `(min, max)`. The store clamps with it and the UI uses it for slider/spinbox limits, so a range is defined once in
  `config.py`. Per-stat target caps come from `config.STAT_VALUE_RANGES`.
- **One shared `Settings` instance** is created in `main.py`. UI tabs mutate it directly and then emit a
  signal from `settings/signals.py`. The controller reads it each tick, so changes apply live with no restart.
  Signals exist only for things that must *react* (e.g. tick rate -> timer interval, overlay visibility).
  **Never cache a section** (`aim = settings.aimbot`) beyond one tick/handler: `Settings.replace_with(other)` (used on profile
  load/reset) swaps the section objects in place on the shared root.
- **Explicit save only.** Changes apply live but are not written to disk until the user clicks Save.
  Unsaved changes show a marker (`*` in the window title + "Unsaved changes" label in the Settings tab).
  Any `settings_changed` signal sets the dirty flag. Save, load and reset clear it.
- **`settings/store.py`:** `to_dict` / `from_dict` (pure) + `ProfileStore` (files).
  - Profiles are `profiles/<name>.json` with readable values: keys as names (`"INSERT"`), enums as strings.
  - **Forgiving load:** unknown keys are ignored, missing keys keep defaults, wrong types / bad enums / bad colours
    fall back to the default, and numbers are clamped. Each problem becomes a warning (logged + `ProfileStore.last_warnings`).
    Only a missing/unreadable file or invalid JSON raises `ProfileError`.
  - **Names:** letters, digits, space, `_`, `-` (max 40), no Windows device names (`CON`, `NUL`, ...).
  - **`default` is read-only:** it can't be saved over, renamed or deleted (use Save as). "Reset to defaults" uses
    `default_settings()` (code), not the file.
  - **Startup:** `load_startup()` -> last used (`profiles/.last_profile`, git-ignored) -> `default.json` -> built-in defaults. Never raises.
  - Saves are atomic (write `.tmp`, then `os.replace`).
- **Versioning:** each profile has `"schema_version"`. `store.CURRENT_SCHEMA_VERSION` (now **1**) and
  `store.MIGRATIONS[from_version] = fn(dict) -> dict` run in order on load. A newer-version profile loads best-effort with a warning.
- **`profiles/default.json` must equal the code defaults** (a test enforces it). Regenerate after changing any default:
  `python -c "from actrainer.settings.store import ProfileStore, default_settings as d; ProfileStore().save('default', d(), allow_read_only=True)"`

### Adding a new setting end-to-end
1. **Model:** add a typed field with a default to the right dataclass in `settings/models.py`. If it's numeric,
   use `ranged(default, config.SOME_RANGE)` and add the range to `config.py`.
2. **Profile:** regenerate `profiles/default.json` (command above). Only if old profiles would load *wrongly*
   (renamed/moved/re-meaning field), bump `CURRENT_SCHEMA_VERSION` and add a migration + test.
3. **UI control:** add the widget in the relevant `ui/tabs/*_tab.py`, initialise it from settings (limits from `field_range`),
   write back on change, emit `settings_changed`. Also refresh it in the tab's `load_from_settings()` (called after a profile load).
4. **Feature:** read the field in the feature module (`features/*.py`) and add a unit test.
5. Update this file (§7 if the pattern changed, §13 status).

---

## 8. Keybind system (`input/keys.py`, `input/actions.py`, `input/keybinds.py`)

- **`keys.py`:** binds are VK codes (ints) in memory and names in JSON (`key_name` / `vk_from_name`). `BINDABLE_VKS` =
  letters, digits, F1-F24, numpad, navigation keys, punctuation, L/R Shift/Ctrl/Alt, and mouse LMB, RMB, MMB, MOUSE4, MOUSE5.
  **Not bindable:** the scroll wheel (can't be polled), generic Shift/Ctrl/Alt 0x10-0x12 (they fire with the L/R
  variants), and **Escape** (clears a bind in the capture).
- **`actions.py`:** `BindMode` (`HOLD` active while held / `TOGGLE` flips per press / `PRESS` fires once on the down edge),
  `Bind(key, mode)`, `ActionDef(id, label, category, allowed_modes, default_mode, default_key)`, the `ACTIONS` registry
  and `default_binds()`. It's a separate module so `settings/models.py` can import defaults without a cycle.
- **`keybinds.py`:** `KeybindEngine.update(pressed_vks, binds, suspended=False) -> ActionStates` (pure).
  `states.is_active(id)` (HOLD held / TOGGLE on), `states.fired(id)` (down edge this tick, any mode).
  `suspended=True` while the menu captures a bind: edges are tracked but nothing fires, so the captured key doesn't trigger
  afterwards. `reset_toggles()` is used by panic. Fed each tick by `winapi.get_pressed_keys(BINDABLE_VKS)`.
- **Actions:** `menu_toggle` (INSERT), `panic` (END), `quit` (unbound), `aimbot` (RMB, HOLD or TOGGLE),
  `aimbot_enable_toggle`, `esp_toggle`, `set_game_fov`, `freeze_game_fov`, and for every stat/weapon `set_<id>` +
  `freeze_<id>` (all unbound, PRESS).
  Everything except `aimbot` is PRESS-only.
- **Registering a new action:**
  1. Add an `ActionDef` in `actions._build_actions()` (use a module constant for its id if the controller references it).
  2. Regenerate `profiles/default.json` (§7).
  3. Handle the action in `app/controller.py` (read its state each tick).
  4. The Keybinds tab lists the registry automatically, so no UI work is needed.
- **Conflicts:** `find_conflicts(binds) -> {vk: [action_ids]}`. The Keybinds tab highlights them. Default binds have none (tested).

---

## 9. Adding a menu tab or widget

- **Controls bound to settings:** use `ui/binder.py`. In a page: `b = SettingBinder(settings, signals, "esp")`, then
  `b.toggle(field, text, description)` (full-width switch row, for booleans), `b.chip(field, text)` (pill toggle, for groups of
  independent options), `b.segmented(field, {Enum: label})` (one-of-N choices; prefer over combos when there are few options),
  `b.slider(field, text, decimals, suffix)` (range from field metadata), `b.combo(...)`, `b.colour(field)` (colour chip + picker). Each control initialises from settings, writes back + emits `settings_changed(section)` on change, and
  registers a loader. `b.load()` refreshes them all quietly. For a bind: `k = KeybindBinder(settings, signals)`, then
  `k.button(action_id)` / `k.mode_segmented(action_id)` (pages) / `k.mode_combo(action_id)` (compact tables). Custom controls: write back + emit yourself, and add a loader that uses `set_quietly`.
- **Page (sidebar section):** create `ui/tabs/<name>_tab.py` with module constants `TITLE` and `SUBTITLE` and a `QWidget`
  subclass taking `(settings, signals[, ...])`. Build cards with `group()`, use `labelled(text, widget)` for label + control rows,
  zero outer margins (the window adds page margins + a scroll area), and implement `load_from_settings()`. Register it in
  `MenuWindow.__init__` (`sections` list), `MenuWindow.all_tabs()` and add a glyph to `NAV_GLYPHS`.
- **Widget:** if a control is used in more than one tab (or is non-trivial), put it in `ui/widgets/`.
  Widgets expose a Qt signal like `valueChanged`. They never know about `Settings`.
- **Sync rules:** any keybind edit emits `settings_changed("keybinds")`, and the menu reloads all tabs (a bind can appear on
  several tabs). Changes from outside the widgets (profile load, reset, panic, hotkeys) emit `refresh_requested`, which reloads all tabs.
- **Styling:** all colours live in `ui/theme.py` (ice-blue accent `ACCENT`, dark text on accent `ACCENT_TEXT`). Pages use
  object names (`primary`, `danger`, `chip`, `segment`, `nav`, `dim`, `warning`, `status`, `pill`, `value`...) and dynamic
  properties (`capturing`, `conflict`, `state`, `first`/`last`) plus `restyle(widget)`. No inline colours in pages
  (only data colours: colour swatches and presets).
- **Design rules:** booleans = switch rows (with a one-line description when it helps), multi-select = chips,
  one-of-few = segmented, numbers = sliders (or spinboxes in tables), colours = colour chips. Every page has a title and subtitle.
- **Checking the look without opening windows:** render offscreen with `QT_QPA_PLATFORM=offscreen` and
  `QT_QPA_FONTDIR=C:/Windows/Fonts` (no text without it), then `widget.grab().save("x.png")`.

### Menu window behaviour
- **Menu toggle** (default `INSERT`, PRESS, rebindable) shows/hides the menu. It's polled in the tick, so it works while the game is focused.
- **Shown:** always-on-top, raised and activated. Centred over the game window the **first** time.
  After that it remembers its position (stored in `GeneralSettings.menu_pos`).
- **Hidden:** fully hidden (not minimised). Focus goes back to the game window.
- **Mouse capture (verified in-game 2026-10-03):** AssaultCube grabs the mouse while playing. On show we
  bring the menu to the foreground. Windows' foreground lock normally blocks this for a background process, so
  `winapi` uses `AttachThreadInput` to the current foreground thread + `SetForegroundWindow` + `BringWindowToTop`.
  Verified: pressing INSERT in-game brings the menu to the front, AssaultCube releases the cursor and the menu is
  immediately clickable. Hiding gives focus (and the mouse grab) back to the game. Fallback if it ever fails: press `Esc` in-game.
- **Menu position** is stored in `general.menu_pos` on hide. It doesn't mark the profile dirty, is saved with the next Save,
  and is kept (not overwritten) when another profile is loaded. Off-screen positions fall back to centring.
- **Close (X) button:** asks "Quit trainer / Hide menu / Cancel". A **Quit** button in the menu exits cleanly
  (unfreezes values, restores the game FOV, closes overlay). There's no default quit key.
- **Single instance:** a second copy shows "already running" and exits (`QLockFile` in the temp dir; a crashed
  instance's stale lock is detected by PID).
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
- **Overlay verified against a live screenshot (Phase 9):** ESP painted over a screen grab of the client area lined up with the
  visible bot (box around the body, head circle on the head). Re-check with the scratch approach: grab the screen, paint
  `build_esp(...)` on it, no windows needed.
- **FFA team values:** ESP "Team mode" (off by default) decides whether team values matter. Off = every bot is an enemy colour.
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
- **Field ids, not offsets, in features:** player values use ids (`health`, `mag:pistol`, `reserve:pistol`). Only
  `game/local_player.py` maps them to offsets, so features never see memory layout.
- **No value writes while dead:** writing health to a dead player can confuse the death state. Freezes resume on respawn;
  set-now while dead is refused with a notice.
- **Write yaw + pitch together:** they're adjacent floats (0x34/0x38). One 8-byte write means the game never sees a half-updated view.
- **Aim origin is `local.head`** (the eye position), not the feet. Body aim = 60% of the feet->head height (scales when crouching).
- **Aimbot needs the game focused:** otherwise holding RMB in the menu (or another app) would yank the view.
- **Smoothing depends on tick rate:** each tick moves 1/smoothing of the remaining angle, so a higher tick rate aims faster.
- **`VIEW_FOV` is the HORIZONTAL fov (verified Phase 8):** live matrix row 0 has length 1.000 = 1/tan(90°/2) and row 1 has length
  1.7777 = 16:9. So `fov_circle_radius(aim_fov, state.fov, width)` is correct as written.
- **View matrix verified in-game (Phase 8):** a point 50 u along your own view direction projects to exactly (960.0, 540.0) on a
  1920x1080 client area. Offset, in-place read, column-major layout and yaw/pitch convention all agree. Re-run
  `tools/phase8_view_matrix.py` after any game update. A "MISMATCH" means the matrix offset moved.
- **The matrix can be all zeros** before the first frame renders. Check `is_sane_matrix` before projecting.
- **Health goes negative on death** (e.g. -54). Use `dead` (`0x318`) for alive/dead, never `health > 0`.
- **Finding offsets by diffing:** take struct snapshots in state A / B / A again (`tools/phase1_dead_diag.py`).
  Values equal in both A snapshots but different in B are "STRONG" candidates. This filters out timers and movement noise.
- **Finding static pointers:** to check which static slots hold an address, scan the module image
  (base + 0x100000..0x1A0000) for the 4-byte little-endian value. Neighbouring values (capacity/count) often reveal
  the source-level layout.
- **Menu focus over the game works** with `win32.force_foreground` (AttachThreadInput + SetForegroundWindow): AC releases
  the mouse when it loses focus. Qt's `activateWindow()` alone is not enough while the game is focused.
- **AC 1.3.0.2's exe has no version resource:** `get_file_version` returns None. The status panel instead checks the offsets
  (local player pointer resolves to a sane player).
- **Qt offscreen rendering has no fonts** unless `QT_QPA_FONTDIR=C:/Windows/Fonts` is set (text is simply missing).
- **Qt stylesheets don't draw CSS border-triangles** for spinbox/combo arrows (you get bars). Use the SVGs in `ui/assets/`;
  `url()` paths need forward slashes (`Path.as_posix()`).
- **`QPushButton#primary` overrides the disabled look**, so it needs its own `:disabled` rule.
- **`app.setQuitOnLastWindowClosed(False)`** is required, or hiding the menu would quit the app.
- **PyQt5 aborts on unhandled exceptions in Qt callbacks** (slots, paintEvent...) since 5.5. `main.log_unhandled` is installed
  as `sys.excepthook`, so they're logged with a traceback instead. The controller tick also catches everything itself.
- **Open the log file only after the single-instance lock:** otherwise a second copy (about to exit) truncates the running
  trainer's `logs/actrainer.log` (found and fixed in Phase 10).
- **The game never clamps `VIEW_FOV`:** any written value renders (30..170 tested). The console's `/fov` limits don't apply, so
  `config.GAME_FOV_RANGE` (30..150) is the only guard. Writing changes the matrix FOV immediately.
- **QTimer default is coarse (~15.6 ms on Windows):** use `Qt.PreciseTimer` for the tick and overlay timers.
- **Bold on `:checked` clips text:** Qt sizes buttons for the normal font, so a bold checked state cuts off the label
  ("Closest to crosshai"). Chips and segments signal selection with colour only.
- **`QGroupBox QWidget {background}` outranks plain type selectors** (2 types beat 1). Buttons and inputs inside cards need
  explicit `QGroupBox QPushButton` etc. rules, and `#primary`/`#danger` need card-scoped rules too (same for the colour popup).
- **Taskbar icon:** without `win32.set_app_user_model_id(...)` (before any window), Windows groups the app under python.exe
  and shows Python's icon.
- **README screenshots:** after any visible UI change, re-run `tools/readme_shots_menu.py` (offscreen, safe) and, with the game
  visible on screen and in a match, `tools/readme_shots_game.py`. The menu script uses a temp showcase profile, so it never
  touches the user's profiles.
- **Logo assets:** regenerate `ui/assets/logo.png` and `docs/assets/logo.png` (256 px, `Qt.SmoothTransformation`) from
  `docs/assets/logo-source.jpg` if the artwork changes. Don't upscale the 32 px .ico: it goes blurry or blocky.
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
- After any game update, re-run the tools in order (phase1 → phase2 → phase8) before trusting the offsets.

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
- [x] Phase 2: Entities: print every bot *(done 2026-10-03; verified in-game)*
- [x] Phase 3: Maths: angles, projection, skeleton + tests *(done 2026-10-03; verified in-game)*
- [x] Phase 4: Settings + keybinds core + tests *(done 2026-10-03; verified with real keys)*
- [x] Phase 5: Menu shell (all tabs wired to settings, profiles, menu hotkey) *(done 2026-10-03; 205 tests; menu focus/mouse release verified in-game)*
- [x] Phase 6: Controller + aimbot *(done 2026-10-03; 229 tests; verified in-game)*
- [x] Phase 7: Player values (set-now, freeze, keybinds) *(done 2026-10-03; 244 tests; verified in-game)*
- [x] Phase 8: View matrix debug script *(done 2026-10-03; 257 tests; verified in-game)*
- [x] Phase 9: Overlay + ESP + FOV circle *(done 2026-10-03; 284 tests; verified in-game)*
- [x] Phase 10: Polish *(done 2026-10-03; 296 tests; verified in-game)*
  - [x] Game FOV slider (user request): set-now / keep-applied / key, range 30..150 (game doesn't clamp; verified), restored on panic/quit
  - [x] Panic also stops keep-applied FOV and restores the original FOV
  - [x] Crash safety (excepthook), single-instance lock, log file opened after the lock
  - [x] Precise timers, Keybinds ⚠ tab badge, startup profile-warnings dialog, View row in the status panel
  - [x] README usage guide, final CLAUDE.md pass, .gitattributes
  - Auto-reattach, status panel and conflict warnings were already done in Phases 5–9 (verified by the user).

- [x] **UI revamp (user request, 2026-10-03)** *(done; 316 tests; approved by the user)*: W Cheat - By BigH branding + logo (header
  top right, window/taskbar icon, README banner), sidebar navigation, page titles, ice-blue theme, toggle switches, chips,
  segmented controls, new colour picker popup with live preview.

- [x] **README screenshots (user request, 2026-10-03)**: in-game ESP (2 styles) + all menu pages + colour picker, with
  regeneration tools.
- [x] **README "How it works" section (user request, 2026-10-03)**: memory/pointers/structs, the camera-pointer
  story, aimbot maths, projection, ESP box/skeleton/FOV circle, overlay, player values, architecture. Keep it in sync if
  the maths or offsets change.

**Next:** nothing planned. Wait for the user's next request. Possible future ideas (only if the user
asks): target lock while holding the aim key, visibility check (needs a raycast or a visibility offset), game-mode offset
for automatic team check, per-profile hotkey to switch profiles.

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
- **2026-10-03:** Added `input/actions.py` (registry + Bind/BindMode) separate from the state machine. models.py needs
  default binds and keybinds.py needs modes; one shared module avoids a circular import.
- **2026-10-03:** Setting ranges are stored as dataclass field metadata (`ranged()`), so store clamping and UI limits share
  one source. Profiles store key NAMES, not VK numbers, so they're readable and hand-editable.
- **2026-10-03:** Player values: one `ValueSetting` per stat (health/armor/grenades/akimbo), one `AmmoSetting` (mag + reserve,
  shared freeze) per weapon. That matches the approved menu sketch and gives 10 set + 10 freeze actions.
- **2026-10-03:** `default` profile is read-only and must equal code defaults (test). Reset uses code defaults.
  Aimbot team check defaults OFF (FFA finding from Phase 2).
- **2026-10-03:** Only `aimbot` allows HOLD/TOGGLE. All other actions are PRESS (set-now fires, toggles flip a setting).
- **2026-10-03:** `app/controller.py` started in Phase 5 (not 6). The menu hotkey must be polled every tick, so a minimal
  controller (keybinds, actions, attach/liveness, status) was needed. Phase 6 adds GameState + aimbot to the same tick.
- **2026-10-03:** Added `ui/binder.py`, `ui/layout.py`, `ui/profile_session.py`, `app/status.py` (not in the original layout).
  The binder removes per-control boilerplate (init/write-back/emit/reload). The session keeps the explicit-save workflow out
  of the widgets. Status is pure data shared by controller and UI.
- **2026-10-03:** `AppSignals` lives in `settings/signals.py` as the single hub for UI <-> controller signals (not just settings).
- **2026-10-03:** Read-only `default`: the Save button is disabled with a tooltip. Use Save as.
- **2026-10-03:** Shared display names (`config.VALUE_NAMES`) so the Player tab and keybind labels match (Armour, SMG...).
- **2026-10-03:** Aimbot runs only while the game window is the foreground window (safety; not in the original spec).
- **2026-10-03:** Target priority ties are broken by angle to the crosshair (crosshair priority breaks ties by distance),
  so the pick is deterministic. No target locking yet: with crosshair priority the target stays the closest while you aim at it.
- **2026-10-03:** `read_game_state` excludes dead bots (every feature ignores them). The view matrix and FOV join it in Phase 8.
- **2026-10-03:** Player value writes are skipped while dead and only happen when the value differs (freeze is free when
  already correct). Set-now is queued and applied inside the next tick's read/write cycle, never directly from the UI thread's click.
- **2026-10-03:** Added `notice` signal + live "Now" column (via `ControllerStatus.player_values`) for feedback in the Player tab.
- **2026-10-03:** Phase 8 verification is mostly automatic: projecting a point along our own view direction must hit the exact
  screen centre. That checks the matrix against the angle convention with no human judgement needed. The game FOV is horizontal
  (derived from the matrix). `GameState` now carries `view_matrix` and `fov`.
- **2026-10-03:** Added ESP `team_mode` (default off) instead of always colouring by team value. FFA bots carry team values
  (Phase 2), which would wrongly mark some as teammates. New field with a default, so no schema bump; default.json regenerated.
- **2026-10-03:** Controller -> overlay via an `OverlayFrame` signal (pure data). The controller never touches the window, and
  overlay visibility logic is unit-testable. The overlay repaints on its own timer at `overlay_fps`.
- **2026-10-03:** ESP box = projected head-top (eye + 0.8 u) to feet, width = 0.45 x height. The aimbot's current target is
  drawn thicker. Furthest players draw first.
- **2026-10-03:** Game FOV (user request) is a separate `view` settings section + `features/game_fov.py`, not a player
  "value": it's a float at a static address, not a player-struct int. Range 30..150 chosen after verifying the game renders any
  value without clamping. Panic/quit restore the original FOV (panic = everything back to normal). Group placed at the top
  of the Player tab so it's visible without scrolling.
- **2026-10-03:** Phase 10 hardening: `sys.excepthook` logger (PyQt5 would otherwise abort), `QLockFile` single instance,
  file logging only after the lock, `Qt.PreciseTimer`.
- **2026-10-03:** UI revamp (user choices): sidebar layout, swatches + picker popup, logo in header/taskbar/README,
  ice-blue accent. Colours apply live while the picker is open; Cancel/Esc restores, Apply/click-outside keeps. Logo moved from
  the project root into `ui/assets/`. When the user then added the 1920 px artwork, all logos switched to 256 px PNGs made
  from it (source kept as `docs/assets/logo-source.jpg`).
- **2026-10-03:** `binder.checkbox` replaced by `toggle` / `chip` / `segmented`. Pages carry `TITLE`/`SUBTITLE`, and
  `MenuWindow` wraps each in a uniform header + scroll area (pages no longer scroll themselves).
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
