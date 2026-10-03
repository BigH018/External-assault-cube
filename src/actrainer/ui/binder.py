"""Connects widgets to settings fields with one line each.

Each `SettingBinder` method creates a control, initialises it from the setting, writes it back on
change, emits `settings_changed(section)`, and registers a loader so `binder.load()` refreshes
every control after a profile load / panic / hotkey (via refresh_requested).

The section is looked up through the root Settings EVERY time (getattr(settings, section)), never
cached, because profile loads replace the section objects (see CLAUDE.md §7).
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import QComboBox, QPushButton, QSpinBox, QWidget

from actrainer.input.actions import ACTIONS_BY_ID, Bind, BindMode
from actrainer.settings.models import Settings, field_range
from actrainer.settings.signals import AppSignals
from actrainer.ui.widgets.colour_button import ColourButton
from actrainer.ui.widgets.keybind_button import KeybindButton
from actrainer.ui.widgets.labelled_slider import LabelledSlider
from actrainer.ui.widgets.segmented import SegmentedControl
from actrainer.ui.widgets.toggle_switch import ToggleRow


class SettingBinder:
    """Binds controls to one settings section ("aimbot", "esp", "general", ...)."""

    def __init__(self, settings: Settings, signals: AppSignals, section: str) -> None:
        self._settings = settings
        self._signals = signals
        self._section = section
        self._loaders: list[Callable[[], None]] = []

    # --- plumbing ---------------------------------------------------------------------

    def obj(self) -> Any:
        """The current section object (looked up fresh each time)."""
        return getattr(self._settings, self._section)

    def get(self, field: str) -> Any:
        return getattr(self.obj(), field)

    def set(self, field: str, value: Any) -> None:
        """Write a value and announce the change (marks the profile dirty)."""
        setattr(self.obj(), field, value)
        self._signals.settings_changed.emit(self._section)

    def add_loader(self, loader: Callable[[], None]) -> None:
        """Register a custom refresh function (for controls not made by this binder)."""
        self._loaders.append(loader)

    def load(self) -> None:
        """Refresh every bound control from settings, without emitting change signals."""
        for loader in self._loaders:
            loader()

    # --- controls -------------------------------------------------------------------------

    def toggle(self, field: str, text: str, description: str = "", tooltip: str = "") -> ToggleRow:
        """A full-width row: label (+ optional description) on the left, on/off switch on the right."""
        row = ToggleRow(text, description)
        row.setToolTip(tooltip)
        switch = row.switch

        def load() -> None:
            switch.blockSignals(True)
            switch.setChecked(bool(self.get(field)))
            switch.blockSignals(False)

        switch.toggled.connect(lambda checked: self.set(field, checked))
        self._loaders.append(load)
        load()
        return row

    def chip(self, field: str, text: str, tooltip: str = "") -> QPushButton:
        """A pill-shaped on/off button, for groups of independent options (e.g. ESP styles)."""
        chip = QPushButton(text)
        chip.setObjectName("chip")
        chip.setCheckable(True)
        chip.setCursor(Qt.PointingHandCursor)
        chip.setToolTip(tooltip)

        def load() -> None:
            set_quietly(chip, chip.setChecked, bool(self.get(field)))

        chip.toggled.connect(lambda checked: self.set(field, checked))
        self._loaders.append(load)
        load()
        return chip

    def segmented(self, field: str, labels: dict[Enum, str]) -> SegmentedControl:
        """Joined buttons for an enum field; exactly one is selected."""
        members = list(labels)
        control = SegmentedControl([labels[m] for m in members])

        def load() -> None:
            control.setCurrentIndex(members.index(self.get(field)))

        control.currentIndexChanged.connect(lambda i: self.set(field, members[i]))
        self._loaders.append(load)
        load()
        return control

    def slider(self, field: str, text: str, decimals: int = 0, suffix: str = "") -> LabelledSlider:
        """Slider whose range comes from the field's metadata (config.py)."""
        rng = field_range(type(self.obj()), field)
        if rng is None:
            raise ValueError(f"{self._section}.{field} has no range metadata")
        slider = LabelledSlider(text, rng[0], rng[1], decimals, suffix)
        is_int = isinstance(self.get(field), int)
        slider.valueChanged.connect(lambda v: self.set(field, int(round(v)) if is_int else float(v)))
        self._loaders.append(lambda: slider.setValue(self.get(field)))
        slider.setValue(self.get(field))
        return slider

    def combo(self, field: str, labels: dict[Enum, str]) -> QComboBox:
        """Drop-down for an enum field. `labels` maps each enum member to its display text."""
        combo = QComboBox()
        members = list(labels)
        for member in members:
            combo.addItem(labels[member])

        def load() -> None:
            combo.blockSignals(True)
            combo.setCurrentIndex(members.index(self.get(field)))
            combo.blockSignals(False)

        combo.currentIndexChanged.connect(lambda i: self.set(field, members[i]))
        self._loaders.append(load)
        load()
        return combo

    def colour(self, field: str) -> ColourButton:
        button = ColourButton(self.get(field))
        button.colourChanged.connect(lambda rgba: self.set(field, rgba))
        self._loaders.append(lambda: button.setColour(self.get(field)))
        return button


MODE_LABELS = {BindMode.HOLD: "Hold", BindMode.TOGGLE: "Toggle", BindMode.PRESS: "Press"}


class KeybindBinder:
    """Creates key buttons / mode selectors wired to settings.keybinds.binds[action_id].

    Any tab can embed the bind for an action next to its own settings (e.g. the aimbot key).
    Edits emit settings_changed("keybinds"); the menu window then reloads every tab, so all views of
    the same bind stay in sync. Capture start/stop is forwarded as bind_capture_changed so the
    controller suspends keybinds while a key is being captured.
    """

    def __init__(self, settings: Settings, signals: AppSignals) -> None:
        self._settings = settings
        self._signals = signals
        self._loaders: list[Callable[[], None]] = []
        self.buttons: dict[str, KeybindButton] = {}

    def bind(self, action_id: str) -> Bind:
        return self._settings.keybinds.binds[action_id]

    def button(self, action_id: str) -> KeybindButton:
        btn = KeybindButton(self.bind(action_id).key)

        def changed(vk: int | None) -> None:
            self.bind(action_id).key = vk
            self._signals.settings_changed.emit("keybinds")

        btn.keyChanged.connect(changed)
        btn.captureStarted.connect(lambda: self._signals.bind_capture_changed.emit(True))
        btn.captureFinished.connect(lambda: self._signals.bind_capture_changed.emit(False))
        self._loaders.append(lambda: btn.setKey(self.bind(action_id).key))
        self.buttons[action_id] = btn
        return btn

    def mode_combo(self, action_id: str) -> QComboBox:
        """Mode drop-down limited to the action's allowed modes (disabled if there's only one)."""
        allowed = list(ACTIONS_BY_ID[action_id].allowed_modes)
        combo = QComboBox()
        for mode in allowed:
            combo.addItem(MODE_LABELS[mode])
        combo.setEnabled(len(allowed) > 1)

        def load() -> None:
            set_quietly(combo, combo.setCurrentIndex, allowed.index(self.bind(action_id).mode))

        def changed(index: int) -> None:
            self.bind(action_id).mode = allowed[index]
            self._signals.settings_changed.emit("keybinds")

        combo.currentIndexChanged.connect(changed)
        self._loaders.append(load)
        load()
        return combo

    def mode_segmented(self, action_id: str) -> SegmentedControl:
        """Mode as joined buttons (e.g. Hold | Toggle) for actions that allow several modes."""
        allowed = list(ACTIONS_BY_ID[action_id].allowed_modes)
        control = SegmentedControl([MODE_LABELS[m] for m in allowed])

        def changed(index: int) -> None:
            self.bind(action_id).mode = allowed[index]
            self._signals.settings_changed.emit("keybinds")

        control.currentIndexChanged.connect(changed)
        self._loaders.append(lambda: control.setCurrentIndex(allowed.index(self.bind(action_id).mode)))
        control.setCurrentIndex(allowed.index(self.bind(action_id).mode))
        return control

    def load(self) -> None:
        for loader in self._loaders:
            loader()


def make_spinbox(minimum: int, maximum: int, value: int, on_change: Callable[[int], None]) -> QSpinBox:
    """Integer spinbox that calls on_change(value) on user edits."""
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    spin.valueChanged.connect(on_change)
    return spin


def set_quietly(widget: QWidget, setter: Callable[[Any], None], value: Any) -> None:
    """Call a widget setter without emitting its change signals."""
    widget.blockSignals(True)
    setter(value)
    widget.blockSignals(False)
