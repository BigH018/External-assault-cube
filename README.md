# AssaultCube Learning Trainer

A personal learning project: an external trainer for **AssaultCube 1.3.0.2** written in Python.
It covers process memory, pointer chains, vector maths, world-to-screen projection, and building a
PyQt5 desktop app with a settings menu and a transparent overlay.

> **Scope:** offline, single-player bot matches on my own PC only. No online use, no anti-cheat
> bypasses or evasion, no injection or DLLs, no network code, no distribution.

## Features (planned)
- Dark-themed PyQt5 menu (toggle with INSERT). All changes apply live.
- Aimbot: hold/toggle key, head/body, target priority, FOV + FOV circle, smoothing, team check, max distance.
- ESP overlay: 2D box, corner box, head circle, approximate skeleton, names, health, distance, snaplines.
- Player values: health, armour, grenades, ammo with set-now, freeze and keybinds.
- Keybinds tab with hold/toggle/press-once modes and conflict warnings.
- JSON profiles with auto-load of the last used profile.
- Panic key (END) disables everything instantly.

## Requirements
- Windows, Python 3.11+
- AssaultCube 1.3.0.2, running **windowed or borderless**

## Install
```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run
Start AssaultCube, begin an offline bot match, then:
```powershell
python -m actrainer
```

## Test
```powershell
python -m pytest
```

See `CLAUDE.md` for architecture, conventions and current status, and `docs/DEVLOG.md` for the build log.
