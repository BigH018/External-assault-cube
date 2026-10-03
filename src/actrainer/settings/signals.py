"""Qt signal hub shared by the UI, the controller and main.py.

The UI edits the shared Settings object directly and then emits `settings_changed(section)`.
The controller reads settings every tick, so most changes need no signal at all. Signals exist
for things that must REACT: the dirty marker, the tick timer interval, refreshing widgets after
something other than the UI changed settings (profile load, panic, a toggle hotkey), etc.
"""

from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal


class AppSignals(QObject):
    """One instance is created in main.py and passed to everything that needs it."""

    # UI -> everyone: a setting in `section` ("general", "aimbot", "esp", "player", "keybinds") was edited.
    settings_changed = pyqtSignal(str)
    # Settings changed from OUTSIDE the widgets (profile load, reset, panic, hotkey): widgets must reload.
    refresh_requested = pyqtSignal()
    # A bind button started (True) / finished (False) capturing a key: keybinds must be suspended meanwhile.
    bind_capture_changed = pyqtSignal(bool)
    # Player tab "Set now" / set hotkey (value id: a stat or weapon). The controller writes it on the next tick.
    set_value_requested = pyqtSignal(str)
    # Player tab "Set game FOV now" / hotkey. The controller writes it on the next tick.
    game_fov_set_requested = pyqtSignal()
    # Controller -> menu.
    menu_toggle_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    status_changed = pyqtSignal(object)  # app.controller.ControllerStatus
    # Controller -> menu: short user-facing message (e.g. "Health set to 999", "Not in a match").
    notice = pyqtSignal(str)
    # Controller -> overlay: features.primitives.OverlayFrame for the next repaint.
    overlay_frame = pyqtSignal(object)
