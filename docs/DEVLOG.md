# Dev Log

Dated log of what was built, decisions made and bugs fixed. Newest first.

---

## 2026-10-03 — Phase 3: Maths

**Built**
- `maths/vectors.py`: Vec3 helpers (add/sub/scale/dot/cross/length/length_2d/distance/normalize/lerp).
- `maths/angles.py`: `Angles`, `calc_aim_angles`, `direction_from_angles`, `normalize_yaw`, `clamp_pitch`, `yaw_delta`
  (shortest signed), `angular_distance` (true angle via dot product), `is_within_fov`, `smooth_angles` (1/smoothing per tick,
  shortest yaw path).
- `maths/projection.py`: `world_to_screen` (column-major, rejects w < 0.001, y flipped), `fov_circle_radius`.
- `maths/skeleton.py`: proportion table (`JOINTS`), `BONES`, `facing_vectors`, `build_skeleton`.
- `tests/helpers/gl_matrix.py`: pure-Python GL matrices + `ac_view_projection()` that mimics AC's `transplayer()`.
- Tests: vectors, angles, projection, skeleton. **107 tests total, all passing.**
- `tools/phase3_angles_check.py`: read-only in-game comparison of your view angles vs `calc_aim_angles`.

**Decisions / findings**
- Yaw formula derived from AC's `vecfromyawpitch()`: forward = (sin yaw, −cos yaw) → `yaw = atan2(dx, −dy)` = `atan2(dy, dx) + 90°`.
- The projection tests build the matrix the way AC's renderer does, so the angle convention and the projection are
  checked against each other. A point along the view direction lands at screen centre for 7 yaw/pitch combos.
- **Bug caught by tests:** skeleton "right" was `forward × up`, which projects to screen-LEFT, because AC's world is
  left-handed ("Z-up LH quake style"). Fixed to `up × forward`.
- FOV check uses the true angle between direction vectors, so it's correct near straight up/down (a 180° yaw difference at
  pitch 89 is only 2°).
- Smoothing speed depends on tick rate (noted for Phase 6).

---

## 2026-10-03 — Phase 2: Entities

**Built**
- `game/entities.py`: `read_player_count` (clamped to `MAX_ENTITIES`), `read_entity_pointers` (whole uint32 array in one
  read), `read_entities(proc, local_address, include_dead=False)`. Skips null/garbage pointers, the local player,
  entries failing the sanity check, unreadable entries and (by default) dead bots. A bad entity is never fatal.
- `tools/phase2_entities.py`: 1 Hz table of every bot + raw slot list.
- `tests/helpers/fake_game.py`: `make_player_buffer()` (moved from test_player) + `FakeProcess`.
- `tests/game/test_entities.py`: 6 tests. 27 tests total, all passing.

**Changes**
- `is_valid_bot`: dead bots now use `BOT_DEAD_HEALTH_MIN` (-1000) as the lower bound. Health goes negative on death
  (Phase 1 finding), so the old 0–100 filter would have thrown dead bots away as garbage.
- CLAUDE.md: Offset change rule (prove → keep old value in a comment → log → flag "OFFSET CHANGED").

**Verified against the running game (FFA deathmatch)**
- Player count 8, slot 0 null, 7 bots with real names (PMB, zaiBan, XP|TheNameless, ...), health 100, sane positions.
- **Finding:** in FFA, bots still have team 0/1, and 3 of 7 share the local player's team (0). This confirms that the
  aimbot/ESP team check must be a user toggle and off for FFA.

---

## 2026-10-03 — Phase 1: Memory (local player)

**Built**
- `pyproject.toml` (src layout, editable install, pytest config). Installed requirements + `pip install -e .`
  and verified imports: pymem OK, PyQt5 5.15.11 / Qt 5.15.2, pytest 9.1.1, actrainer 0.1.0.
- `config.py`: non-offset constants (process name, pointer/world/health sanity limits).
- `offsets.py`: all 1.3.0.2 offsets + `PLAYER_READ_SIZE`.
- `memory/process.py`: `GameProcess` (attach/detach/is_alive, module base, typed u32/i32/f32 reads and writes).
  pymem errors are wrapped into `AttachError` / `MemoryAccessError`.
- `game/structs.py`: `Vec3`, `PlayerSnapshot`, `GameState` (frozen dataclasses).
- `game/player.py`: one-read struct parsing (`parse_player` is pure) + validity checks.
- `game/local_player.py`: follow the local-player pointer and read/validate the local player.
- `tools/phase1_local_player.py`: live debug print with auto-reattach.
- `tests/game/test_player.py`: parser and validity tests.

**Decisions**
- Added `game/player.py` (not in the original layout). Struct parsing and validity checks are shared by the local
  player (Phase 1) and the entity list (Phase 2), so they live in one place.
- Each player struct is read in **one** `ReadProcessMemory` call (`PLAYER_READ_SIZE` = 0x31C bytes) and unpacked
  locally. That's about 20× fewer cross-process calls per player than reading field by field.
- Bytes are unpacked with explicit `struct` formats (`<I`, `<i`, `<f`) rather than pymem's `read_int`/`read_long`,
  so the 32-bit sizes are explicit.
- Local player validity = valid pointer + sane position (+ a very wide health range). Never health 0–100,
  because the trainer can set health to 999. Bots keep a loose 0–100 filter.
- `winapi/win32.py` started early with just `is_key_down` (needed by the dead-flag diagnostic).

**Bug: `dead` stayed 0 after dying (FFA deathmatch)**
- Validity check ruled out: local health range is -1000..1e6 and a rejected player prints "No valid local player",
  not stale values. Added a test that dead players with health 0 / -20 / -150 stay valid.
- Wrote `tools/phase1_dead_diag.py` (F9 snapshots alive / dead / alive, diffs the 0x31C struct).
- Run 1: the local player pointer **changed** on death (0x009DD2C8 → 0x00595410). The "dead" snapshot had a different
  vtable at +0x00, an empty name, and the ASCII path `packages\models\weapons\grenade\static\shadows.dat` where ammo
  should be. We were reading a different object.
- Root cause: `0x17E0A8` is `camera1`, not `player1`. Scanned module static memory for slots holding the player
  address: hits at +0x17E0A8, +0x17E254, +0x18AC00, +0x195404. `+0x18AC00` sits right before the `players` vector
  (buf 0x18AC04, capacity 16 at 0x18AC08, count 8 at 0x18AC0C), which matches `playerent *player1; vector<playerent*> players;`.
- **Fix:** `LOCAL_PLAYER_PTR` → `0x18AC00`. Old value kept as `CAMERA_PTR`.
- Run 2: player pointer stable, camera switches to the death-cam and back, `dead@0x318` 0 → 1 → 0, health -54 while dead.
  `DEAD` offset was correct all along. A byte at `0x76` also flips 0 → 1 (likely the state enum), noted as a backup.
- Other observations (unverified, not used): 0x10–0x18 look like velocity floats; 0x18C / 0x1E4 increment on
  death (frags/deaths counters?).

---

## 2026-10-03 — Step 0: Project setup

- Private GitHub repo `BigH018/assault-cube-project`.
- CLAUDE.md, README.md, requirements.txt, .gitignore. Plan and layout approved.
- `platform/` renamed to `winapi/` (stdlib shadowing). Added `config.py`, `game/state.py`, `features/primitives.py`.
