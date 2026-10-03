"""Virtual-key codes <-> human-readable names, including mouse buttons.

Binds are stored as VK codes (ints) in memory and as names in JSON profiles, so profiles are
readable and hand-editable ("INSERT", "MOUSE4", "F5").

Notes:
- The scroll wheel can't be polled with GetAsyncKeyState, so it isn't bindable.
- Generic Shift/Ctrl/Alt (0x10-0x12) are left out on purpose. They report "down" together with
  the left/right variants, so a capture would pick the wrong one. Use LSHIFT/RSHIFT etc. instead.
- Escape is reserved: in the bind capture it means "clear this bind".
"""

from __future__ import annotations

VK_ESCAPE = 0x1B
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_INSERT = 0x2D
VK_END = 0x23

_NAMED: dict[int, str] = {
    0x01: "LMB", 0x02: "RMB", 0x04: "MMB", 0x05: "MOUSE4", 0x06: "MOUSE5",
    0x08: "BACKSPACE", 0x09: "TAB", 0x0D: "ENTER", 0x14: "CAPSLOCK", 0x20: "SPACE",
    0x21: "PAGEUP", 0x22: "PAGEDOWN", 0x23: "END", 0x24: "HOME",
    0x25: "LEFT", 0x26: "UP", 0x27: "RIGHT", 0x28: "DOWN",
    0x2D: "INSERT", 0x2E: "DELETE",
    0x6A: "NUM*", 0x6B: "NUM+", 0x6D: "NUM-", 0x6E: "NUM.", 0x6F: "NUM/",
    0xA0: "LSHIFT", 0xA1: "RSHIFT", 0xA2: "LCTRL", 0xA3: "RCTRL", 0xA4: "LALT", 0xA5: "RALT",
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/", 0xC0: "`",
    0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}
_NAMED.update({0x30 + i: str(i) for i in range(10)})            # top-row digits
_NAMED.update({0x41 + i: chr(ord("A") + i) for i in range(26)})  # letters
_NAMED.update({0x60 + i: f"NUM{i}" for i in range(10)})          # numpad digits
_NAMED.update({0x70 + i: f"F{i + 1}" for i in range(24)})        # F1..F24

VK_TO_NAME: dict[int, str] = dict(sorted(_NAMED.items()))
NAME_TO_VK: dict[str, int] = {name: vk for vk, name in VK_TO_NAME.items()}

# Every key the bind capture listens for (Escape is handled separately, as "clear").
BINDABLE_VKS: tuple[int, ...] = tuple(VK_TO_NAME)

UNBOUND_NAME = "Unbound"


def key_name(vk: int | None) -> str:
    """Display name for a VK code ("Unbound" for None, "VK 0x.." for unknown codes)."""
    if vk is None:
        return UNBOUND_NAME
    return VK_TO_NAME.get(vk, f"VK 0x{vk:02X}")


def vk_from_name(name: str | None) -> int | None:
    """VK code for a key name (case-insensitive), or None if unknown/unbound."""
    if not name:
        return None
    return NAME_TO_VK.get(name.upper())  # "Unbound" isn't in the table, so it maps to None too
