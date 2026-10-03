"""Phase 1 debug script: live-print the local player's position, angles, health and team.

Run:  python tools\\phase1_local_player.py      (Ctrl+C to stop)

Waits for ac_client.exe, then prints a line a few times per second. If the game closes it goes
back to waiting, so you can start and stop the game freely.
"""

from __future__ import annotations

import logging
import time

from actrainer import offsets
from actrainer.game.local_player import get_local_player_address, read_local_player
from actrainer.memory.process import AttachError, GameProcess, MemoryAccessError

PRINT_INTERVAL_S = 0.2
RETRY_INTERVAL_S = 1.0


def wait_for_game(proc: GameProcess) -> None:
    """Block until we can attach to the game."""
    print("Waiting for ac_client.exe ...")
    while True:
        try:
            proc.attach()
            print(f"Attached: pid {proc.pid}, module base 0x{proc.module_base:08X} "
                  f"(offsets for v{offsets.GAME_VERSION})")
            return
        except AttachError:
            time.sleep(RETRY_INTERVAL_S)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    proc = GameProcess()
    wait_for_game(proc)
    try:
        while True:
            try:
                player = read_local_player(proc)
                if player is None:
                    ptr = get_local_player_address(proc)
                    shown = f"0x{ptr:08X}" if ptr is not None else "null"
                    print(f"No valid local player (pointer {shown}) - in menu or between matches?")
                else:
                    print(f"{player.name:<15} | ptr 0x{player.address:08X} | feet {player.feet} "
                          f"| head {player.head} | yaw {player.yaw:6.1f} pitch {player.pitch:6.1f} "
                          f"| hp {player.health:4d} ar {player.armor:3d} | team {player.team} "
                          f"| dead {int(player.dead)}")
            except MemoryAccessError as exc:
                if proc.is_alive():
                    print(f"Read error (skipping): {exc}")
                else:
                    print("Game closed.")
                    proc.detach()
                    wait_for_game(proc)
            time.sleep(PRINT_INTERVAL_S)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        proc.detach()


if __name__ == "__main__":
    main()
