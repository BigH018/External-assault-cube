"""ctypes wrappers around the Win32 API.

Phase 1 only needs global key state. Window lookup, client rect, DPI awareness, foreground
handling and extended window styles are added in later phases.
"""

from __future__ import annotations

import ctypes

_user32 = ctypes.WinDLL("user32", use_last_error=True)

_user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
_user32.GetAsyncKeyState.restype = ctypes.c_short

# GetAsyncKeyState sets the most significant bit of its 16-bit result while the key is held down.
_KEY_DOWN_MASK = 0x8000


def is_key_down(vk: int) -> bool:
    """True if the key/mouse button with virtual-key code `vk` is held right now.

    Works globally, even while the game window has focus. That's why hotkeys poll this
    instead of using Qt key events.
    """
    return bool(_user32.GetAsyncKeyState(vk) & _KEY_DOWN_MASK)
