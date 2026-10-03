# Dev Log

Dated log of what was built, decisions made and bugs fixed. Newest first.

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
