"""Keybinds tab: every bindable action from the registry, grouped by category, with conflict warnings.

Built automatically from input.actions.ACTIONS, so new actions appear here with no UI work.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from actrainer.input.actions import ACTIONS, ACTIONS_BY_ID
from actrainer.input.keybinds import find_conflicts
from actrainer.input.keys import key_name
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.ui.binder import KeybindBinder
from actrainer.ui.layout import group, hint

TITLE = "Keybinds"
SUBTITLE = "Every action you can put on a key or mouse button. Keys work while the game is focused."

WARNING_ICON = "⚠"
MODE_COLUMN_WIDTH = 90
WARNING_COLUMN_WIDTH = 20


class KeybindsTab(QWidget):
    def __init__(self, settings: Settings, signals: AppSignals) -> None:
        super().__init__()
        self._settings = settings
        self.keys = KeybindBinder(settings, signals)
        self._warnings: dict[str, QLabel] = {}

        self._banner = QLabel()
        self._banner.setObjectName("warning")
        self._banner.setWordWrap(True)

        content = QVBoxLayout(self)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(12)
        content.addWidget(hint("Click a key button, then press any key or mouse button. Esc clears the bind."))
        content.addWidget(self._banner)

        categories: dict[str, list] = {}
        for action in ACTIONS:
            categories.setdefault(action.category, []).append(action)
        for category, actions in categories.items():
            box, grid = group(category, grid=True)
            for r, action in enumerate(actions):
                warning = QLabel()
                warning.setObjectName("danger")
                self._warnings[action.id] = warning
                grid.addWidget(QLabel(action.label), r, 0)
                grid.addWidget(self.keys.button(action.id), r, 1)
                mode = self.keys.mode_combo(action.id)
                mode.setFixedWidth(MODE_COLUMN_WIDTH)
                warning.setFixedWidth(WARNING_COLUMN_WIDTH)
                grid.addWidget(mode, r, 2)
                grid.addWidget(warning, r, 3)
            grid.setColumnStretch(0, 1)
            content.addWidget(box)
        content.addStretch(1)
        self._update_conflicts()

    def load_from_settings(self) -> None:
        self.keys.load()
        self._update_conflicts()

    def _update_conflicts(self) -> None:
        conflicts = find_conflicts(self._settings.keybinds.binds)
        conflicting = {action_id: vk for vk, ids in conflicts.items() for action_id in ids}
        for action_id, warning in self._warnings.items():
            if action_id in conflicting:
                vk = conflicting[action_id]
                others = [ACTIONS_BY_ID[a].label for a in conflicts[vk] if a != action_id]
                text = f"{key_name(vk)} is also bound to: {', '.join(others)}"
                warning.setText(WARNING_ICON)
                warning.setToolTip(text)
                self.keys.buttons[action_id].setConflict(True, text)
            else:
                warning.setText("")
                warning.setToolTip("")
                self.keys.buttons[action_id].setConflict(False)
        if conflicts:
            lines = [f"{key_name(vk)} → {', '.join(ACTIONS_BY_ID[a].label for a in ids)}" for vk, ids in conflicts.items()]
            self._banner.setText(f"{WARNING_ICON} Conflicting binds (one key triggers several actions):\n" + "\n".join(lines))
            self._banner.show()
        else:
            self._banner.hide()
