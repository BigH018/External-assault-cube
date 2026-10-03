"""The current profile name + unsaved-changes flag, and the profile actions the menu offers.

Owns the explicit-save workflow: every settings_changed marks the session dirty; load, save,
save-as and reset clear it. Loads and resets copy the new settings INTO the shared Settings object
(Settings.replace_with), then emit refresh_requested so every widget reloads.
"""

from __future__ import annotations

import logging

from PyQt5.QtCore import QObject, pyqtSignal

from actrainer.settings.models import Settings
from actrainer.settings.signals import AppSignals
from actrainer.settings.store import ProfileStore, default_settings

log = logging.getLogger(__name__)


class ProfileSession(QObject):
    """Emits state_changed() whenever the profile name, dirty flag or profile list changes."""

    state_changed = pyqtSignal()

    def __init__(self, store: ProfileStore, settings: Settings, signals: AppSignals, current: str) -> None:
        super().__init__()
        self.store = store
        self.settings = settings
        self.signals = signals
        self.current = current
        self.dirty = False
        signals.settings_changed.connect(self._on_settings_changed)

    @property
    def read_only(self) -> bool:
        """True when the current profile can't be overwritten (Save must become Save as)."""
        return self.store.is_read_only(self.current)

    def profiles(self) -> list[str]:
        return self.store.list_profiles()

    def mark_dirty(self) -> None:
        if not self.dirty:
            self.dirty = True
            self.state_changed.emit()

    # --- actions (raise ProfileError on failure; the UI shows the message) ---------------------

    def load(self, name: str) -> list[str]:
        """Load a profile into the shared settings. Returns any load warnings."""
        loaded = self.store.load(name)
        self._apply(loaded)
        self.current = self.store.validate_name(name)
        self.store.set_last_profile(self.current)
        self._clean()
        return list(self.store.last_warnings)

    def save(self) -> None:
        """Overwrite the current profile (ProfileError if it's read-only)."""
        self.store.save(self.current, self.settings)
        self.store.set_last_profile(self.current)
        self._clean()

    def save_as(self, name: str) -> None:
        name = self.store.validate_name(name)
        self.store.save(name, self.settings)
        self.current = name
        self.store.set_last_profile(name)
        self._clean()

    def rename(self, old: str, new: str) -> None:
        self.store.rename(old, new)
        if old == self.current:
            self.current = self.store.validate_name(new)
        self.state_changed.emit()

    def delete(self, name: str) -> None:
        self.store.delete(name)
        self.state_changed.emit()

    def reset_to_defaults(self) -> None:
        """Replace settings with the built-in defaults (not saved until the user saves)."""
        self._apply(default_settings())
        self.mark_dirty()

    # --- internals --------------------------------------------------------------------

    def _apply(self, new: Settings) -> None:
        # Keep the window position: it's a property of this session, not of the profile being loaded.
        menu_pos = self.settings.general.menu_pos
        self.settings.replace_with(new)
        self.settings.general.menu_pos = menu_pos
        self.signals.refresh_requested.emit()

    def _clean(self) -> None:
        self.dirty = False
        self.state_changed.emit()

    def _on_settings_changed(self, _section: str) -> None:
        self.mark_dirty()
