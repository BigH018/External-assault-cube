"""README screenshots, part 1: the live game with ESP drawn by the overlay's own painter (no windows shown).

Run:  python tools\\readme_shots_game.py      (AssaultCube running, in a match, game visible on screen)

Grabs the game's client area from the screen and paints build_esp(...) on it, exactly what the overlay
draws, in two style variants. Saves docs/screenshots/esp.jpg and esp-skeleton.jpg (1280x720).
"""

import sys
from dataclasses import replace
from pathlib import Path

from actrainer.winapi import win32

win32.set_dpi_aware()  # before QApplication, so the grab uses real pixels

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from actrainer.features.esp import build_esp  # noqa: E402
from actrainer.game.state import read_game_state  # noqa: E402
from actrainer.memory.process import GameProcess  # noqa: E402
from actrainer.overlay.painter import paint  # noqa: E402
from actrainer.settings.models import AimbotSettings, EspSettings  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
SIZE = (1280, 720)
JPG_QUALITY = 90

VARIANTS = {
    "esp.jpg": (replace(EspSettings(), enabled=True, box_2d=True, head_circle=True, show_name=True,
                        show_health_bar=True, show_distance=True),
                AimbotSettings(enabled=True, draw_fov=True, fov_deg=15.0, fov_thickness=2)),
    "esp-skeleton.jpg": (replace(EspSettings(), enabled=True, box_2d=False, corner_box=True, skeleton=True,
                                 show_name=True, show_health_bar=True, show_health_number=True, show_distance=False,
                                 thickness=2, enemy_colour="#8EC9FFFF"),
                         AimbotSettings(enabled=False)),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    proc = GameProcess()
    proc.attach()
    hwnd = win32.find_main_window(proc.pid)
    x, y, w, h = win32.get_client_rect_on_screen(hwnd)
    state = read_game_state(proc)
    if state is None:
        print("Not in a match.")
        return
    shot = app.primaryScreen().grabWindow(0, x, y, w, h).toImage()
    print(f"{len(state.entities)} bots on the map")
    for name, (esp, aim) in VARIANTS.items():
        image = shot.copy()
        painter = QPainter(image)
        paint(painter, build_esp(state, esp, aim, w, h))
        painter.end()
        image.scaled(*SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(str(OUT / name), "JPG", JPG_QUALITY)
        print("saved", OUT / name)


if __name__ == "__main__":
    main()
