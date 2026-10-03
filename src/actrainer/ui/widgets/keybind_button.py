"""'Press a key to bind' button.

Click it, then press any key or mouse button to assign it; Escape clears the bind.
Capture polls GetAsyncKeyState (via winapi), the same way binds are detected at runtime, so
keyboard keys and mouse buttons work identically and capture works even if focus moves.

Gotcha: the click that starts capture is itself a left-click. So capture first waits until every
key is released, and only then accepts a press. Otherwise every bind would become LMB.
"""

from __future__ import annotations

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QWidget

from actrainer.input.keys import BINDABLE_VKS, VK_ESCAPE, key_name
from actrainer.ui.theme import restyle
from actrainer.winapi import win32

POLL_INTERVAL_MS = 15
CAPTURE_TIMEOUT_MS = 6000
CAPTURE_TEXT = "Press a key… (Esc clears)"
_WATCHED_VKS = (*BINDABLE_VKS, VK_ESCAPE)


class KeybindButton(QPushButton):
    """Shows the bound key. Emits keyChanged(vk or None) after a capture."""

    keyChanged = pyqtSignal(object)  # int | None
    captureStarted = pyqtSignal()
    captureFinished = pyqtSignal()

    def __init__(self, vk: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("keybind")
        self.setToolTip("Click, then press a key or mouse button. Esc clears.")
        self._vk = vk
        self._capturing = False
        self._waiting_for_release = False
        self._poll = QTimer(self)
        self._poll.setInterval(POLL_INTERVAL_MS)
        self._poll.timeout.connect(self._tick)
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.setInterval(CAPTURE_TIMEOUT_MS)
        self._timeout.timeout.connect(lambda: self._finish(cancelled=True))
        self.clicked.connect(self._start)
        self._refresh_text()

    def key(self) -> int | None:
        return self._vk

    def setKey(self, vk: int | None) -> None:  # noqa: N802 (Qt naming)
        """Set the shown key without emitting keyChanged."""
        self._vk = vk
        self._refresh_text()

    def setConflict(self, conflict: bool, tooltip: str = "") -> None:  # noqa: N802
        """Highlight the button red when its key is also bound elsewhere."""
        self.setProperty("conflict", conflict)
        self.setToolTip(tooltip or "Click, then press a key or mouse button. Esc clears.")
        restyle(self)

    def is_capturing(self) -> bool:
        return self._capturing

    # --- capture ------------------------------------------------------------------

    def _start(self) -> None:
        if self._capturing:
            self._finish(cancelled=True)  # clicking again cancels
            return
        self._capturing = True
        self._waiting_for_release = True
        self.setText(CAPTURE_TEXT)
        self.setProperty("capturing", True)
        restyle(self)
        self.captureStarted.emit()
        self._poll.start()
        self._timeout.start()

    def _tick(self) -> None:
        pressed = win32.get_pressed_keys(_WATCHED_VKS)
        if self._waiting_for_release:
            if not pressed:
                self._waiting_for_release = False  # everything released: now accept the next press
            return
        if not pressed:
            return
        if VK_ESCAPE in pressed:
            self._vk = None
        else:
            self._vk = min(pressed)  # if several went down in the same 15 ms, pick one deterministically
        self._finish(cancelled=False)

    def _finish(self, cancelled: bool) -> None:
        self._poll.stop()
        self._timeout.stop()
        self._capturing = False
        self.setProperty("capturing", False)
        restyle(self)
        self._refresh_text()
        self.captureFinished.emit()
        if not cancelled:
            self.keyChanged.emit(self._vk)

    def _refresh_text(self) -> None:
        self.setText(key_name(self._vk))
