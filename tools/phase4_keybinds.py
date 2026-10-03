"""Phase 4 check: the keybind engine with REAL key presses (works while the game is focused).

Run:  python tools\\phase4_keybinds.py      (Ctrl+C in this terminal to stop)

Uses the default binds, plus two extra test actions so every mode can be tried:
    INSERT  -> menu_toggle  (PRESS: prints once per press)
    END     -> panic        (PRESS)
    RMB     -> aimbot       (HOLD: "ACTIVE" while held)
    F6      -> test_toggle  (TOGGLE: flips on/off each press)
    MOUSE4  -> test_press   (PRESS, mouse side button)
Only prints when something changes.
"""

from __future__ import annotations

import time

from actrainer.input.actions import Bind, BindMode, default_binds
from actrainer.input.keybinds import KeybindEngine, find_conflicts
from actrainer.input.keys import BINDABLE_VKS, key_name
from actrainer.winapi.win32 import get_pressed_keys

TICK_S = 1 / 60
VK_F6 = 0x75
VK_XBUTTON1 = 0x05


def main() -> None:
    binds = default_binds()
    binds["test_toggle"] = Bind(VK_F6, BindMode.TOGGLE)
    binds["test_press"] = Bind(VK_XBUTTON1, BindMode.PRESS)
    bound = {a: b for a, b in binds.items() if b.key is not None}
    print("Bound actions:")
    for action_id, b in bound.items():
        print(f"  {key_name(b.key):<8} {b.mode.value:<7} {action_id}")
    print(f"Conflicts: {find_conflicts(binds) or 'none'}")
    print("Press keys (game can be focused). Ctrl+C here to stop.\n")

    engine = KeybindEngine()
    previous_active: frozenset[str] = frozenset()
    try:
        while True:
            states = engine.update(get_pressed_keys(BINDABLE_VKS), binds)
            for action_id in sorted(states.pressed):
                print(f"{time.strftime('%H:%M:%S')}  PRESSED  {action_id}")
            for action_id in sorted(states.active - previous_active):
                print(f"{time.strftime('%H:%M:%S')}  ACTIVE   {action_id}")
            for action_id in sorted(previous_active - states.active):
                print(f"{time.strftime('%H:%M:%S')}  inactive {action_id}")
            previous_active = states.active
            time.sleep(TICK_S)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
