"""Phase 2 debug script: live table of every bot's name, health, team and head position.

Run:  python tools\\phase2_entities.py      (Ctrl+C to stop)

Refreshes once a second. Dead bots are shown too (marked DEAD) so you can watch them die and respawn.
Also prints the raw slot table so you can see null slots and the local player's slot.
"""

from __future__ import annotations

import logging
import math
import time

from actrainer import offsets
from actrainer.game.entities import read_entities, read_entity_pointers, read_player_count
from actrainer.game.local_player import read_local_player
from actrainer.game.structs import Vec3
from actrainer.memory.process import AttachError, GameProcess, MemoryAccessError

REFRESH_INTERVAL_S = 1.0
RETRY_INTERVAL_S = 1.0


def distance(a: Vec3, b: Vec3) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def wait_for_game(proc: GameProcess) -> None:
    print("Waiting for ac_client.exe ...")
    while True:
        try:
            proc.attach()
            print(f"Attached: pid {proc.pid}, module base 0x{proc.module_base:08X} (v{offsets.GAME_VERSION})")
            return
        except AttachError:
            time.sleep(RETRY_INTERVAL_S)


def print_frame(proc: GameProcess) -> None:
    local = read_local_player(proc)
    local_addr = local.address if local else None
    slots = read_entity_pointers(proc)
    bots = read_entities(proc, local_addr, include_dead=True)

    print("\n" + "=" * 100)
    if local:
        print(f"LOCAL  {local.name:<15} ptr 0x{local.address:08X}  hp {local.health:4d}  team {local.team}  "
              f"head {local.head}{'  DEAD' if local.dead else ''}")
    else:
        print("LOCAL  (no valid local player)")
    print(f"player count {read_player_count(proc)} | slots: "
          + " ".join("null" if s == 0 else ("LOCAL" if s == local_addr else f"0x{s:08X}") for s in slots))
    print(f"{'name':<16}{'ptr':<12}{'hp':>5}{'armor':>7}{'team':>6}  {'head position':<30}{'dist':>8}  state")
    for bot in bots:
        dist = f"{distance(local.head, bot.head):8.1f}" if local else "       -"
        print(f"{bot.name:<16}0x{bot.address:08X}{bot.health:>5}{bot.armor:>7}{bot.team:>6}  "
              f"{str(bot.head):<30}{dist}  {'DEAD' if bot.dead else 'alive'}")
    valid_slots = sum(1 for s in slots if s and s != local_addr)
    print(f"{len(bots)} bots shown ({valid_slots} non-null non-local slots)")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    proc = GameProcess()
    wait_for_game(proc)
    try:
        while True:
            try:
                print_frame(proc)
            except MemoryAccessError as exc:
                if proc.is_alive():
                    print(f"Read error (skipping): {exc}")
                else:
                    print("Game closed.")
                    proc.detach()
                    wait_for_game(proc)
            time.sleep(REFRESH_INTERVAL_S)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        proc.detach()


if __name__ == "__main__":
    main()
