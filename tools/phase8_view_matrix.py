"""Phase 8 debug script: verify the view matrix and world_to_screen against the real game.

Run:  python tools\\phase8_view_matrix.py      (Ctrl+C to stop)

Prints twice a second:
  - the game's client area size and FOV
  - CENTRE CHECK: a point 50 units straight along YOUR view direction is projected. It must land
    at the exact screen centre. That proves the matrix offset, its column-major layout and our yaw/pitch
    convention all agree. This needs no human judgement.
  - the bot nearest your crosshair: its head and feet in screen pixels (or BEHIND if off-camera).
    Point your crosshair at its head: the head x,y should be close to the centre.
Read-only: nothing is written.
"""

from __future__ import annotations

import time

from actrainer import offsets
from actrainer.game.state import read_game_state
from actrainer.game.view import horizontal_fov_from_matrix, is_sane_matrix, read_fov, read_view_matrix
from actrainer.maths import vectors
from actrainer.maths.angles import Angles, angular_distance, calc_aim_angles, direction_from_angles
from actrainer.maths.projection import world_to_screen
from actrainer.memory.process import AttachError, GameProcess, MemoryAccessError
from actrainer.winapi import win32

REFRESH_S = 0.5
CENTRE_CHECK_DISTANCE = 50.0
CENTRE_TOLERANCE_PX = 2.0


def fmt(point: tuple[float, float] | None) -> str:
    return "BEHIND" if point is None else f"({point[0]:7.1f}, {point[1]:7.1f})"


def main() -> None:
    win32.set_dpi_aware()  # so the client rect is in real pixels, like the overlay will use
    proc = GameProcess()
    try:
        proc.attach()
    except AttachError as exc:
        print(f"Start AssaultCube first: {exc}")
        return
    hwnd = win32.find_main_window(proc.pid)
    print(f"Attached (pid {proc.pid}); view matrix at base+0x{offsets.VIEW_MATRIX:X} (in place, column-major)")
    try:
        while True:
            try:
                rect = win32.get_client_rect_on_screen(hwnd) if hwnd else None
                state = read_game_state(proc)
                matrix = read_view_matrix(proc)
                fov = read_fov(proc)
                if rect is None or state is None or not is_sane_matrix(matrix):
                    print("Waiting for a match / game window ...")
                    time.sleep(REFRESH_S)
                    continue
                _, _, w, h = rect
                local = state.local
                view = Angles(local.yaw, local.pitch)

                ahead = vectors.add(local.head, vectors.scale(direction_from_angles(view), CENTRE_CHECK_DISTANCE))
                centre = world_to_screen(ahead, matrix, w, h)
                ok = centre is not None and abs(centre[0] - w / 2) <= CENTRE_TOLERANCE_PX \
                    and abs(centre[1] - h / 2) <= CENTRE_TOLERANCE_PX
                matrix_fov = horizontal_fov_from_matrix(matrix)
                line = (f"client {w}x{h} | fov {fov:5.1f} (matrix hfov {matrix_fov:5.1f}) | "
                        f"centre check {fmt(centre)} vs ({w / 2:.1f}, {h / 2:.1f}) {'OK' if ok else 'MISMATCH'}")

                if state.entities:
                    bot = min(state.entities, key=lambda b: angular_distance(view, calc_aim_angles(local.head, b.head)))
                    line += (f" | {bot.name:<15} head {fmt(world_to_screen(bot.head, matrix, w, h))} "
                             f"feet {fmt(world_to_screen(bot.feet, matrix, w, h))}")
                print(line)
            except MemoryAccessError as exc:
                print(f"Read error: {exc}")
            time.sleep(REFRESH_S)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        proc.detach()


if __name__ == "__main__":
    main()
