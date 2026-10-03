"""Phase 1 diagnostic: find which bytes of the player struct change when you die.

Run:  python tools\\phase1_dead_diag.py

Press F9 IN-GAME three times (you'll hear a beep each time):
  1. while ALIVE
  2. while DEAD (after killing yourself, before respawning)
  3. ALIVE again (after respawning)
Press F10 to quit early.

Then it prints:
  - the local player pointer at each snapshot (in case it changes on death)
  - what health/dead read at each snapshot
  - every 4-byte-aligned offset that changed between snapshot 1 and 2, as int32, float and bytes
  - "STRONG" candidates: offsets equal in both alive snapshots but different while dead.
    A real dead/state flag should show up here.
"""

from __future__ import annotations

import struct
import time
import winsound

from actrainer import offsets
from actrainer.game.local_player import get_local_player_address
from actrainer.game.player import parse_player
from actrainer.memory.process import AttachError, GameProcess
from actrainer.winapi.win32 import is_key_down

VK_F9 = 0x78
VK_F10 = 0x79
POLL_INTERVAL_S = 0.02
BEEP_HZ = 880
BEEP_MS = 120
LABELS = ("ALIVE #1", "DEAD", "ALIVE #2")

# Known field names, so the diff is easier to read.
_KNOWN = {
    offsets.HEAD_POS: "head.x", offsets.HEAD_POS + 4: "head.y", offsets.HEAD_POS + 8: "head.z",
    offsets.FEET_POS: "feet.x", offsets.FEET_POS + 4: "feet.y", offsets.FEET_POS + 8: "feet.z",
    offsets.VIEW_YAW: "yaw", offsets.VIEW_PITCH: "pitch", offsets.HEALTH: "health",
    offsets.ARMOR: "armor", offsets.GRENADES: "grenades", offsets.AKIMBO_AMMO: "akimbo",
    offsets.TEAM: "team", offsets.DEAD: "dead (current offset)",
    **{off: f"mag.{w}" for w, off in offsets.MAG_AMMO.items()},
    **{off: f"reserve.{w}" for w, off in offsets.RESERVE_AMMO.items()},
}


def wait_for_f9() -> bool:
    """Block until F9 is pressed and released. Returns False if F10 was pressed instead."""
    while True:
        if is_key_down(VK_F10):
            return False
        if is_key_down(VK_F9):
            while is_key_down(VK_F9):  # wait for release so one press = one snapshot
                time.sleep(POLL_INTERVAL_S)
            return True
        time.sleep(POLL_INTERVAL_S)


def take_snapshot(proc: GameProcess) -> tuple[int, bytes]:
    """Return (local player pointer, raw struct bytes). Also prints the camera pointer for comparison."""
    addr = get_local_player_address(proc)
    if addr is None:
        raise RuntimeError("local player pointer is null/invalid - are you in a match?")
    camera = proc.read_u32(proc.module_base + offsets.CAMERA_PTR)
    same = "same as player" if camera == addr else "DIFFERENT from player"
    print(f"  player ptr 0x{addr:08X} | camera ptr 0x{camera:08X} ({same})")
    return addr, proc.read_bytes(addr, offsets.PLAYER_READ_SIZE)


def i32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<i", buf, off)[0]


def f32(buf: bytes, off: int) -> float:
    return struct.unpack_from("<f", buf, off)[0]


def print_report(snaps: list[tuple[int, bytes]]) -> None:
    a1, dead, a2 = (buf for _, buf in snaps)
    size = offsets.PLAYER_READ_SIZE

    print("\n=== Pointers / parsed fields ===")
    for label, (addr, buf) in zip(LABELS, snaps):
        p = parse_player(buf, addr)
        print(f"{label:<9} ptr 0x{addr:08X}  health {p.health:5d}  armor {p.armor:4d}  "
              f"dead@0x{offsets.DEAD:X} = {i32(buf, offsets.DEAD)}  feet {p.feet}")

    print("\n=== int32-aligned offsets that changed ALIVE #1 -> DEAD ===")
    print(f"{'offset':>7} | {'ALIVE#1':>11} {'DEAD':>11} {'ALIVE#2':>11} | {'float DEAD':>12} | "
          f"bytes ALIVE#1 -> DEAD   | note")
    for off in range(0, size - 3, 4):
        if a1[off:off + 4] == dead[off:off + 4]:
            continue
        strong = a1[off:off + 4] == a2[off:off + 4]
        note = _KNOWN.get(off, "")
        if strong:
            note = ("STRONG  " + note).strip()
        print(f"  0x{off:03X} | {i32(a1, off):>11} {i32(dead, off):>11} {i32(a2, off):>11} | "
              f"{f32(dead, off):>12.4g} | {a1[off:off + 4].hex(' ')} -> {dead[off:off + 4].hex(' ')} | {note}")

    print("\n=== STRONG byte candidates (same in both ALIVE snapshots, different when DEAD) ===")
    found = False
    for off in range(size):
        if a1[off] == a2[off] != dead[off]:
            found = True
            print(f"  0x{off:03X}: alive {a1[off]:3d} (0x{a1[off]:02X})  dead {dead[off]:3d} (0x{dead[off]:02X})")
    if not found:
        print("  (none)")
    changed_bytes = sum(1 for i in range(size) if a1[i] != dead[i])
    print(f"\n{changed_bytes} bytes changed between ALIVE #1 and DEAD.")


def main() -> None:
    proc = GameProcess()
    try:
        proc.attach()
    except AttachError as exc:
        print(f"Start AssaultCube first: {exc}")
        return
    print(f"Attached (pid {proc.pid}). Press F9 in-game: {', then '.join(LABELS)}. F10 quits.")

    snaps: list[tuple[int, bytes]] = []
    try:
        for label in LABELS:
            print(f"Waiting for F9 ({label}) ...")
            if not wait_for_f9():
                print("Quit.")
                return
            snaps.append(take_snapshot(proc))
            winsound.Beep(BEEP_HZ, BEEP_MS)
            print(f"  captured {label}")
        print_report(snaps)
    finally:
        proc.detach()


if __name__ == "__main__":
    main()
