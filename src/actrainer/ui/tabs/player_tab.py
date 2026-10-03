"""Player page: game FOV, health, armour, grenades, akimbo and per-weapon ammo.

Each value has a target, a live "Now" readout, "Set now" (the controller writes it on the next tick),
a key for set-now, and a Freeze switch (the controller re-applies the value every tick). This page only
edits settings and emits requests. The memory writes happen in the controller.
"""

from __future__ import annotations

from collections.abc import Callable

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from actrainer import config
from actrainer.app.status import ControllerStatus
from actrainer.game.local_player import mag_field, reserve_field
from actrainer.input.actions import SET_GAME_FOV, set_action_id
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.ui.binder import KeybindBinder, SettingBinder, make_spinbox, set_quietly
from actrainer.ui.layout import group, hint, labelled, row
from actrainer.ui.widgets.toggle_switch import ToggleSwitch

TITLE = "Player"
SUBTITLE = "Set or freeze your health, armour, grenades and ammo, and change the game's field of view."

NOTICE_CLEAR_MS = 4000
NO_VALUE = "–"


class PlayerTab(QWidget):
    def __init__(self, settings: Settings, signals: AppSignals) -> None:
        super().__init__()
        self._settings = settings
        self._signals = signals
        self.keys = KeybindBinder(settings, signals)
        self._loaders: list[Callable[[], None]] = []
        self._now_labels: dict[str, tuple[QLabel, list[str]]] = {}  # value id -> (label, field ids)

        self.notice = QLabel()
        self.notice.setObjectName("warning")
        self._notice_timer = QTimer(self)
        self._notice_timer.setSingleShot(True)
        self._notice_timer.setInterval(NOTICE_CLEAR_MS)
        self._notice_timer.timeout.connect(self.notice.clear)
        signals.notice.connect(self.show_notice)

        # --- game FOV ---
        self.view_binder = SettingBinder(settings, signals, "view")
        view, vg = group("Game FOV")
        self.fov_now = QLabel(NO_VALUE)
        self.fov_now.setObjectName("value")
        self.fov_now.setToolTip("Current in-game FOV")
        fov_set = QPushButton("Set now")
        fov_set.setObjectName("primary")
        fov_set.clicked.connect(signals.game_fov_set_requested.emit)
        vg.addWidget(self.view_binder.slider("fov", "Field of view", suffix="°"))
        vg.addWidget(labelled("Current", row(self.fov_now, fov_set, self.keys.button(SET_GAME_FOV), stretch_last=True)))
        vg.addWidget(self.view_binder.toggle("freeze", "Keep applied", "Re-apply your FOV whenever the game changes it."))
        vg.addWidget(hint("The game's own horizontal FOV (what /fov changes, default 90). Panic and quitting restore "
                          "the FOV you had before."))

        # --- stats + ammo ---
        stats, sg = group("Stats", grid=True)
        self._header(sg, ["", "Target", "Now", "", "Key", "Freeze"])
        for r, stat in enumerate(config.STAT_VALUES, start=1):
            self._stat_row(sg, r, stat)

        ammo, ag = group("Ammo", grid=True)
        self._header(ag, ["", "Magazine", "Reserve", "Now", "", "Key", "Freeze"])
        for r, weapon in enumerate(config.WEAPONS, start=1):
            self._weapon_row(ag, r, weapon)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.notice)
        layout.addWidget(view)
        layout.addWidget(stats)
        layout.addWidget(ammo)
        layout.addWidget(hint("Values are only written while you're in a match and alive. Freeze toggle keys are on "
                              "the Keybinds page."))
        layout.addStretch(1)

    # --- rows ---------------------------------------------------------------------------

    @staticmethod
    def _header(grid: QGridLayout, titles: list[str]) -> None:
        for col, title in enumerate(titles):
            label = QLabel(title)
            label.setObjectName("dim")
            grid.addWidget(label, 0, col)

    def _set_now_button(self, value_id: str) -> QPushButton:
        button = QPushButton("Set now")
        button.clicked.connect(lambda: self._signals.set_value_requested.emit(value_id))
        return button

    def _freeze_switch(self, get_setting: Callable[[], object]) -> ToggleSwitch:
        switch = ToggleSwitch()
        switch.setToolTip("Freeze: keep re-applying this value")

        def changed(checked: bool) -> None:
            get_setting().freeze = checked  # type: ignore[attr-defined]
            self._signals.settings_changed.emit("player")

        switch.toggled.connect(changed)
        self._loaders.append(lambda: set_quietly(switch, switch.setChecked, get_setting().freeze))  # type: ignore[attr-defined]
        return switch

    def _now_label(self, value_id: str, fields: list[str]) -> QLabel:
        label = QLabel(NO_VALUE)
        label.setObjectName("value")
        label.setToolTip("Current in-game value")
        self._now_labels[value_id] = (label, fields)
        return label

    def _stat_row(self, grid: QGridLayout, r: int, stat: str) -> None:
        setting = lambda: self._settings.player.values[stat]  # noqa: E731 (fresh lookup every time)
        lo, hi = config.STAT_VALUE_RANGES[stat]

        def changed(v: int) -> None:
            setting().target = v
            self._signals.settings_changed.emit("player")

        spin = make_spinbox(lo, hi, setting().target, changed)
        self._loaders.append(lambda: set_quietly(spin, spin.setValue, setting().target))
        grid.addWidget(QLabel(config.VALUE_NAMES[stat]), r, 0)
        grid.addWidget(spin, r, 1)
        grid.addWidget(self._now_label(stat, [stat]), r, 2)
        grid.addWidget(self._set_now_button(stat), r, 3)
        grid.addWidget(self.keys.button(set_action_id(stat)), r, 4)
        grid.addWidget(self._freeze_switch(setting), r, 5, Qt.AlignCenter)

    def _weapon_row(self, grid: QGridLayout, r: int, weapon: str) -> None:
        setting = lambda: self._settings.player.ammo[weapon]  # noqa: E731

        def mag_changed(v: int) -> None:
            setting().mag = v
            self._signals.settings_changed.emit("player")

        def reserve_changed(v: int) -> None:
            setting().reserve = v
            self._signals.settings_changed.emit("player")

        mag = make_spinbox(*config.MAG_AMMO_RANGE, setting().mag, mag_changed)
        reserve = make_spinbox(*config.RESERVE_AMMO_RANGE, setting().reserve, reserve_changed)
        self._loaders.append(lambda: set_quietly(mag, mag.setValue, setting().mag))
        self._loaders.append(lambda: set_quietly(reserve, reserve.setValue, setting().reserve))
        grid.addWidget(QLabel(config.VALUE_NAMES[weapon]), r, 0)
        grid.addWidget(mag, r, 1)
        grid.addWidget(reserve, r, 2)
        grid.addWidget(self._now_label(weapon, [mag_field(weapon), reserve_field(weapon)]), r, 3)
        grid.addWidget(self._set_now_button(weapon), r, 4)
        grid.addWidget(self.keys.button(set_action_id(weapon)), r, 5)
        grid.addWidget(self._freeze_switch(setting), r, 6, Qt.AlignCenter)

    # --- live feedback ------------------------------------------------------------------

    def show_status(self, status: ControllerStatus) -> None:
        """Update the "Now" readouts from the controller's latest snapshot."""
        for label, fields in self._now_labels.values():
            values = [status.player_values.get(f) for f in fields]
            label.setText(NO_VALUE if None in values else " / ".join(str(v) for v in values))
        self.fov_now.setText(f"{status.game_fov:g}°" if status.game_fov else NO_VALUE)

    def show_notice(self, text: str) -> None:
        self.notice.setText(text)
        self._notice_timer.start()

    def load_from_settings(self) -> None:
        for loader in self._loaders:
            loader()
        self.keys.load()
        self.view_binder.load()
