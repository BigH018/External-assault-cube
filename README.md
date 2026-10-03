<p align="center">
  <img src="docs/assets/logo.png" width="160" alt="W Cheat logo">
</p>

<h1 align="center">W Cheat</h1>

<p align="center">
  <b>By BigH</b><br>
  External trainer for AssaultCube 1.3.0.2, written in Python<br>
  <sub>Personal learning project · offline bot matches only</sub>
</p>

---

A personal learning project: an external trainer for **AssaultCube 1.3.0.2**, written in Python.
It covers process memory, pointer chains, vector maths, world-to-screen projection, and building a
PyQt5 desktop app with a settings menu and a transparent overlay.

> **Scope:** offline, single-player bot matches on my own PC only. No online use, no anti-cheat
> bypasses or evasion, no injection or DLLs, no network code, no distribution.

## Screenshots

<p align="center">
  <img src="docs/screenshots/esp.jpg" width="100%" alt="ESP in-game: boxes, head circles, names, health bars, distance and the FOV circle">
  <br><sub><b>ESP:</b> 2D boxes, head circles, names, health bars, distance and the aimbot FOV circle (bots seen through walls)</sub>
</p>

<p align="center">
  <img src="docs/screenshots/esp-skeleton.jpg" width="100%" alt="ESP in-game: corner boxes, skeletons and health numbers">
  <br><sub><b>ESP:</b> corner boxes, approximate skeletons and health numbers in a custom colour</sub>
</p>

<table>
  <tr>
    <td align="center" width="50%"><img src="docs/screenshots/menu-aimbot.png" alt="Aimbot page"><br><sub><b>Aimbot</b>: key and mode, targeting, FOV, smoothing</sub></td>
    <td align="center" width="50%"><img src="docs/screenshots/menu-esp.png" alt="ESP page"><br><sub><b>ESP</b>: styles, colours and info</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/screenshots/menu-player.png" alt="Player page"><br><sub><b>Player</b>: game FOV, set/freeze values with live readouts</sub></td>
    <td align="center"><img src="docs/screenshots/colour-picker.png" alt="Colour picker"><br><sub><b>Colour picker</b>: presets, custom colour, opacity, live preview</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/screenshots/menu-keybinds.png" alt="Keybinds page"><br><sub><b>Keybinds</b>: every action, any key or mouse button</sub></td>
    <td align="center"><img src="docs/screenshots/menu-settings.png" alt="Settings page"><br><sub><b>Settings</b>: profiles, performance, live status</sub></td>
  </tr>
</table>

<sub>Screenshots are regenerated with <code>tools\readme_shots_game.py</code> and <code>tools\readme_shots_menu.py</code>.
The ESP images are the game with the overlay's own drawing applied, captured with the same painter the overlay uses.</sub>

## Features
- **Menu:** dark PyQt5 window with sidebar navigation, toggle switches and an ice-blue accent, toggled with **INSERT**.
  Every change applies live. Profiles use explicit Save.
- **Aimbot:** hold/toggle key, head/body, priority (crosshair / distance / lowest health), FOV radius + circle,
  smoothing, team check, max distance. Only aims while the game window is focused.
- **ESP overlay:** 2D box, corner box, head circle, approximate skeleton (combinable); name, health bar, health number,
  distance, snaplines; team mode; colours (picker with presets, custom colour, opacity, live preview) and line
  thickness. Transparent and click-through.
- **Player values:** health, armour, grenades, akimbo, and magazine/reserve ammo per weapon. Each has Set now, Freeze
  and an optional hotkey, plus a live in-game readout.
- **Game FOV:** change the game's own field of view (30–150°), set once or keep applied.
- **Keybinds:** every action is bindable to a keyboard key or mouse button, in hold / toggle / press mode, with conflict warnings.
- **Panic (END):** instantly disables everything, unfreezes all values and restores your original FOV.

## Requirements
- Windows, Python 3.11+
- AssaultCube 1.3.0.2, running **windowed or borderless** (the overlay can't draw over exclusive fullscreen)

## Install
```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run
1. Start AssaultCube and begin an **offline bot match**.
2. Run `python -m actrainer`. The menu opens, and the header shows **● Attached · N bots · 60 Hz**.
   Pick a section in the left sidebar.
3. Press **INSERT** to hide or show the menu at any time, including from inside the game.

The trainer can be started before the game. It attaches automatically within about a second of the game starting, and
reattaches if the game is restarted. Logs go to the console and to `logs\actrainer.log`.

## Using the menu
| Page | What's there |
|---|---|
| **Aimbot** | Enable, activation key and mode (default: hold **right mouse button**), aim at head/body, priority, max distance, team check (leave off in free-for-all), FOV radius + "draw FOV circle", smoothing (1 = instant snap) |
| **ESP** | Enable, toggle key, team mode (off for free-for-all), enemies only, styles (click the chips to combine), line thickness, enemy/team colours, info extras, snapline origin |
| **Player** | Game FOV (slider, Set now, Keep applied); stats and ammo, each with target, live "Now" value, Set now, key and Freeze |
| **Keybinds** | Every bindable action. Click a key button, then press any key or mouse button; **Esc** clears. Conflicts show in red, and the sidebar entry gets a ⚠ |
| **Settings** | Profiles (Save / Save as / Load / Rename / Delete), Reset to defaults, tick rate, overlay FPS, menu hotkey, status panel |

### Choosing colours
Click any colour chip (e.g. **#FF4040 · 100%**) to open the picker:
- **Presets:** one click; your current opacity is kept.
- **Colour square + hue bar:** for any custom colour.
- **Opacity:** slider in %. The swatches sit on a checkerboard so you can see transparency.
- **Hex:** type `#RRGGBB` or `#RRGGBBAA`.

The colour applies **live** while the picker is open, so you can judge it on real bots. **Apply** (or clicking outside)
keeps it; **Cancel** or **Esc** puts the old colour back. Click **Old** to jump back to the original.

### Default hotkeys
| Key | Action |
|---|---|
| INSERT | Show / hide the menu |
| END | Panic: disable everything, unfreeze values, restore FOV |
| Right mouse (hold) | Aimbot (when enabled) |

Everything else is unbound by default. Bind what you like on the Keybinds tab.

### Profiles
- Changes apply immediately but are only saved when you click **Save**. A `*` in the title means unsaved changes.
- `default` is read-only: use **Save as** to create your own. The last profile you used loads automatically on startup.
- Profiles are readable JSON files in `profiles\`. If one contains invalid values, they're reset or clamped and you're told which.

## Troubleshooting
| Problem | Fix |
|---|---|
| "Not attached" | Start AssaultCube. If the game runs as administrator, run the trainer as administrator too. |
| "Attached · not in a match" | Start or join an offline bot match. The main menu has no player to read. |
| Menu not clickable when it pops up | Press Esc in-game to free the cursor, then INSERT again. |
| No overlay | Run the game windowed or borderless, enable ESP, and keep the game (or the menu) focused. |
| ESP boxes offset | Check Windows display scaling isn't overriding DPI for Python. Run `python tools\phase8_view_matrix.py`: it should say `OK`. |
| "W Cheat is already running" | Another copy is open. Use INSERT to find its menu, or quit it. |
| After a game update | Run `tools\phase1_local_player.py`, `phase2_entities.py` and `phase8_view_matrix.py` to check the offsets still work. |

## Debug tools
Small read-only scripts in `tools\`, one per build phase. Each prints live values from the game:
`phase1_local_player.py`, `phase1_dead_diag.py`, `phase2_entities.py`, `phase3_angles_check.py`, `phase4_keybinds.py`,
`phase8_view_matrix.py`.
README screenshots: `readme_shots_game.py` (game + ESP) and `readme_shots_menu.py` (menu pages).

## Tests
```powershell
python -m pytest
```
316 tests cover the maths, settings/profiles, keybinds, aimbot, ESP, player values, controller and UI. They need no game
and open no windows.

## Project docs
- `CLAUDE.md`: architecture, rules, offsets, gotchas, decision log and status (the project's memory).
- `docs\DEVLOG.md`: dated build log, including the bugs found and how they were fixed.
