"""Phase 3 in-game check: does calc_aim_angles agree with where you're actually looking?

Run:  python tools\\phase3_angles_check.py      (Ctrl+C to stop)

Put your crosshair on a bot's head. The bot closest to your crosshair is shown with:
  - your current yaw/pitch (read from memory)
  - the yaw/pitch calc_aim_angles says you'd need to look at its head
  - the angular distance between the two (should be close to 0 when you're on target)
Read-only: nothing is written to the game.
"""

from __future__ import annotations

import time

from actrainer.game.entities import read_entities
from actrainer.game.local_player import read_local_player
from actrainer.maths.angles import Angles, angular_distance, calc_aim_angles, yaw_delta
from actrainer.memory.process import AttachError, GameProcess, MemoryAccessError

REFRESH_INTERVAL_S = 0.25


def main() -> None:
    proc = GameProcess()
    try:
        proc.attach()
    except AttachError as exc:
        print(f"Start AssaultCube first: {exc}")
        return
    print("Aim at a bot's head. Ctrl+C to stop.")
    try:
        while True:
            try:
                local = read_local_player(proc)
                bots = read_entities(proc, local.address if local else None)
                if local is None or not bots:
                    print("No local player or no live bots.")
                else:
                    view = Angles(local.yaw, local.pitch)
                    # Pick the bot nearest to the crosshair (smallest angle from our view).
                    best = min(bots, key=lambda b: angular_distance(view, calc_aim_angles(local.head, b.head)))
                    need = calc_aim_angles(local.head, best.head)
                    print(f"{best.name:<16} view yaw {view.yaw:6.1f} pitch {view.pitch:6.1f} | "
                          f"needed yaw {need.yaw:6.1f} pitch {need.pitch:6.1f} | "
                          f"yaw diff {yaw_delta(view.yaw, need.yaw):+6.1f} pitch diff {need.pitch - view.pitch:+6.1f} | "
                          f"off by {angular_distance(view, need):5.1f} deg")
            except MemoryAccessError as exc:
                print(f"Read error: {exc}")
            time.sleep(REFRESH_INTERVAL_S)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        proc.detach()


if __name__ == "__main__":
    main()
