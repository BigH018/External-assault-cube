"""README screenshots, part 2: every menu page + the colour picker, rendered offscreen with live game status.

Run:  python tools\\readme_shots_menu.py      (AssaultCube running and in a match, for live status values)

Uses a throwaway showcase profile store (temp dir), so your own profiles are never touched or shown.
Saves docs/screenshots/menu-*.png and colour-picker.png.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"  # offscreen Qt has no fonts without this

from PyQt5.QtCore import QPoint, QRect  # noqa: E402
from PyQt5.QtGui import QColor, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from actrainer.app.status import ControllerStatus  # noqa: E402
from actrainer.game.local_player import VALUE_FIELD_OFFSETS, snapshot_value  # noqa: E402
from actrainer.game.state import read_game_state  # noqa: E402
from actrainer.input.actions import ESP_TOGGLE, freeze_action_id, set_action_id  # noqa: E402
from actrainer.memory.process import GameProcess  # noqa: E402
from actrainer.settings.models import Settings  # noqa: E402
from actrainer.settings.signals import AppSignals  # noqa: E402
from actrainer.settings.store import ProfileStore, default_settings  # noqa: E402
from actrainer.ui.menu_window import MenuWindow  # noqa: E402
from actrainer.ui.profile_session import ProfileSession  # noqa: E402
from actrainer.ui.theme import apply_theme  # noqa: E402
from actrainer.ui.widgets.colour_button import ColourButton  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
PAGES = ["aimbot", "esp", "player", "keybinds", "settings"]
VK_F2, VK_F5, VK_F6 = 0x71, 0x74, 0x75
SHADOW_ALPHAS = (60, 40, 20)


def showcase_settings() -> Settings:
    """A tidy example configuration for the pictures."""
    s = default_settings()
    s.aimbot.enabled = True
    s.esp.enabled = True
    s.esp.head_circle = True
    s.keybinds.binds[ESP_TOGGLE].key = VK_F2
    s.keybinds.binds[set_action_id("health")].key = VK_F5
    s.keybinds.binds[freeze_action_id("health")].key = VK_F6
    s.player.values["health"].target = 999
    s.player.values["health"].freeze = True
    s.player.ammo["assault"].freeze = True
    return s


def live_status() -> ControllerStatus:
    """Status built from the running game (falls back to 'not attached' if it isn't running)."""
    proc = GameProcess()
    try:
        proc.attach()
    except Exception:  # noqa: BLE001 - screenshots still work without the game
        return ControllerStatus()
    state = read_game_state(proc)
    status = ControllerStatus(
        attached=True, pid=proc.pid, module_base=proc.module_base, offsets_ok=state is not None,
        in_match=state is not None, entity_count=len(state.entities) if state else 0, tick_rate=60.0,
        game_focused=True, game_fov=state.fov if state else 0.0,
        player_values={f: snapshot_value(state.local, f) for f in VALUE_FIELD_OFFSETS} if state else {},
    )
    proc.detach()
    return status


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    apply_theme(app)
    settings = showcase_settings()
    store = ProfileStore(Path(tempfile.mkdtemp()))
    store.save("default", default_settings(), allow_read_only=True)
    store.save("BigH", settings)
    store.save("legit", default_settings())

    signals = AppSignals()
    session = ProfileSession(store, settings, signals, "BigH")
    menu = MenuWindow(settings, signals, session, lambda: None)
    menu.reload_all()
    menu.show_status(live_status())
    menu.show()

    for name, tab in zip(PAGES, menu.all_tabs()):
        menu.show_page(tab)
        app.processEvents()
        menu.grab().save(str(OUT / f"menu-{name}.png"))
        print("saved", OUT / f"menu-{name}.png")

    # Colour picker composited onto the ESP page, where the real popup would open for the Enemy colour chip.
    menu.show_page(menu.esp_tab)
    app.processEvents()
    page = menu.grab()
    chip = menu.esp_tab.findChildren(ColourButton)[0]
    chip.open_picker()
    app.processEvents()
    popup = chip.popup.grab()
    anchor = chip.mapTo(menu, QPoint(0, chip.height() + 4))
    if anchor.y() + popup.height() > page.height():  # same rule as ColourPopup.show_below: flip above when no room
        anchor = chip.mapTo(menu, QPoint(0, -popup.height() - 4))
    painter = QPainter(page)
    shadow = QRect(anchor.x() + 4, anchor.y() + 6, popup.width(), popup.height())
    for i, alpha in enumerate(SHADOW_ALPHAS):  # soft drop shadow
        painter.fillRect(shadow.adjusted(-i, -i, i + 2, i + 2), QColor(0, 0, 0, alpha))
    painter.drawPixmap(anchor, popup)
    painter.end()
    page.save(str(OUT / "colour-picker.png"))
    print("saved", OUT / "colour-picker.png")


if __name__ == "__main__":
    main()
