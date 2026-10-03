"""Settings tab: profiles (load/save/save as/rename/delete/reset), performance, menu hotkey, status."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFormLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from actrainer import offsets
from actrainer.app.status import ControllerStatus
from actrainer.input.actions import MENU_TOGGLE
from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.settings.store import ProfileError
from actrainer.ui.binder import KeybindBinder, SettingBinder
from actrainer.ui.layout import group, hint, labelled, row
from actrainer.ui.profile_session import ProfileSession
from actrainer.ui.theme import restyle

CURRENT_MARK = "●  "
READ_ONLY_MARK = "  (read-only)"


class SettingsTab(QWidget):
    def __init__(self, settings: Settings, signals: AppSignals, session: ProfileSession) -> None:
        super().__init__()
        self.session = session
        self.binder = SettingBinder(settings, signals, "general")
        self.keys = KeybindBinder(settings, signals)

        # --- profiles ---
        profiles, p = group("Profiles")
        self.current_label = QLabel()
        self.unsaved_label = QLabel("● Unsaved changes")
        self.unsaved_label.setObjectName("warning")
        p.addWidget(row(self.current_label, None, self.unsaved_label))
        self.list = QListWidget()
        self.list.setMinimumHeight(110)
        self.list.itemDoubleClicked.connect(lambda _item: self._load())
        p.addWidget(self.list)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("primary")
        buttons = [(self.save_button, self._save), (QPushButton("Save as…"), self._save_as),
                   (QPushButton("Load"), self._load), (QPushButton("Rename…"), self._rename),
                   (QPushButton("Delete"), self._delete)]
        for button, handler in buttons:
            button.clicked.connect(handler)
        p.addWidget(row(*(b for b, _ in buttons), stretch_last=True))

        # --- performance + menu ---
        perf, f = group("Performance")
        f.addWidget(self.binder.slider("tick_rate_hz", "Tick rate", suffix=" Hz"))
        f.addWidget(self.binder.slider("overlay_fps", "Overlay FPS"))
        f.addWidget(hint("Tick rate = how often the trainer reads the game and runs features. "
                         "Aim smoothing is per tick, so a higher rate aims faster."))

        menu, m = group("Menu")
        reset = QPushButton("Reset to defaults")
        reset.setObjectName("danger")
        reset.clicked.connect(self._reset)
        m.addWidget(row(QLabel("Menu hotkey"), self.keys.button(MENU_TOGGLE), None, reset))

        # --- status ---
        status, s = group("Status")
        form = QFormLayout()
        s.addLayout(form)
        self.status_labels: dict[str, QLabel] = {}
        for key, title in (("game", "Game"), ("process", "Process"), ("offsets", "Offsets"),
                           ("entities", "Entities"), ("view", "View"), ("tick", "Tick rate")):
            label = QLabel("–")
            label.setObjectName("status")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.status_labels[key] = label
            form.addRow(title, label)

        layout = QVBoxLayout(self)
        for box in (profiles, perf, menu, status):
            layout.addWidget(box)
        layout.addStretch(1)

        session.state_changed.connect(self.refresh_profiles)
        self.refresh_profiles()
        self.show_status(ControllerStatus())

    # --- profiles -----------------------------------------------------------------------

    def refresh_profiles(self) -> None:
        s = self.session
        self.current_label.setText(f"Current: <b>{s.current}</b>{READ_ONLY_MARK if s.read_only else ''}")
        self.unsaved_label.setVisible(s.dirty)
        self.save_button.setEnabled(not s.read_only)
        self.save_button.setToolTip(f"'{s.current}' is read-only: use Save as…" if s.read_only else "")
        self.list.clear()
        for name in s.profiles():
            item = QListWidgetItem((CURRENT_MARK if name == s.current else "    ") + name)
            item.setData(Qt.UserRole, name)
            self.list.addItem(item)
            if name == s.current:
                self.list.setCurrentItem(item)

    def _selected(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _run(self, action, *args) -> bool:  # noqa: ANN001 (callable + its args)
        """Run a session action, showing ProfileError messages instead of crashing."""
        try:
            result = action(*args)
        except ProfileError as exc:
            QMessageBox.warning(self, "Profile", str(exc))
            return False
        if isinstance(result, list) and result:
            QMessageBox.information(self, "Profile loaded with warnings",
                                    "Some settings were invalid and were reset or adjusted:\n\n• " + "\n• ".join(result))
        return True

    def _confirm_discard(self) -> bool:
        if not self.session.dirty:
            return True
        answer = QMessageBox.question(self, "Unsaved changes",
                                      f"Discard unsaved changes to '{self.session.current}'?")
        return answer == QMessageBox.Yes

    def _save(self) -> None:
        self._run(self.session.save)

    def _save_as(self) -> None:
        name, ok = QInputDialog.getText(self, "Save profile as", "Profile name:")
        if not ok or not name.strip():
            return
        if self.session.store.exists(name) and QMessageBox.question(
                self, "Overwrite?", f"Profile '{name.strip()}' exists. Overwrite it?") != QMessageBox.Yes:
            return
        self._run(self.session.save_as, name)

    def _load(self) -> None:
        name = self._selected()
        if name and self._confirm_discard():
            self._run(self.session.load, name)

    def _rename(self) -> None:
        old = self._selected()
        if not old:
            return
        new, ok = QInputDialog.getText(self, "Rename profile", f"New name for '{old}':", text=old)
        if ok and new.strip() and new.strip() != old:
            self._run(self.session.rename, old, new)

    def _delete(self) -> None:
        name = self._selected()
        if name and QMessageBox.question(self, "Delete profile", f"Delete '{name}'? This can't be undone.") \
                == QMessageBox.Yes:
            self._run(self.session.delete, name)

    def _reset(self) -> None:
        if QMessageBox.question(self, "Reset to defaults",
                                "Reset every setting to the built-in defaults? (Not saved until you click Save.)") \
                == QMessageBox.Yes:
            self.session.reset_to_defaults()

    # --- status -----------------------------------------------------------------------------

    def show_status(self, status: ControllerStatus) -> None:
        def put(key: str, text: str, state: str) -> None:
            label = self.status_labels[key]
            label.setText(text)
            label.setProperty("state", state)
            restyle(label)

        if status.attached:
            version = status.exe_version or "exe has no version info"
            put("game", f"Attached · {version}", "ok")
            put("process", f"pid {status.pid} · base 0x{status.module_base:08X}", "ok")
            put("offsets", f"v{offsets.GAME_VERSION} · " + ("local player OK" if status.offsets_ok
                                                          else "no local player (menu / loading?)"),
                "ok" if status.offsets_ok else "warn")
        else:
            put("game", "Not attached: start AssaultCube (windowed or borderless)", "bad")
            put("process", "–", "warn")
            put("offsets", f"v{offsets.GAME_VERSION}", "warn")
        put("entities", str(status.entity_count), "ok" if status.entity_count else "warn")
        if status.attached and status.game_fov:
            focus = "game focused" if status.game_focused else "game not focused"
            put("view", f"FOV {status.game_fov:g}° · {focus}", "ok" if status.game_focused else "warn")
        else:
            put("view", "–", "warn")
        put("tick", f"{status.tick_rate:.1f} Hz", "ok" if status.tick_rate else "warn")

    def load_from_settings(self) -> None:
        self.binder.load()
        self.keys.load()
