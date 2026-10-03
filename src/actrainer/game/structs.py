"""Pure data types describing the game world. No I/O, no pymem, no Qt.

All snapshots are frozen: once read, a tick's data never changes underneath the features using it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Vec3:
    """A 3D point/vector in AssaultCube world units. z is UP."""

    x: float
    y: float
    z: float

    def __str__(self) -> str:
        return f"({self.x:8.2f}, {self.y:8.2f}, {self.z:8.2f})"


@dataclass(frozen=True, slots=True)
class PlayerSnapshot:
    """Everything we read about one player (local player or bot) in a single tick."""

    address: int            # where this player struct lives in game memory
    name: str
    head: Vec3
    feet: Vec3
    yaw: float              # degrees, 0..360 (AC convention; see maths/angles.py)
    pitch: float            # degrees, -90..90
    health: int
    armor: int
    team: int
    dead: bool
    mag_ammo: dict[str, int] = field(default_factory=dict)       # weapon -> rounds in magazine
    reserve_ammo: dict[str, int] = field(default_factory=dict)   # weapon -> spare rounds
    grenades: int = 0
    akimbo_ammo: int = 0


@dataclass(frozen=True, slots=True)
class GameState:
    """One tick's view of the game: the local player, every other valid player, and the camera."""

    local: PlayerSnapshot
    entities: tuple[PlayerSnapshot, ...] = ()
    view_matrix: tuple[float, ...] = ()   # 16 floats, OpenGL column-major (projection x modelview)
    fov: float = 0.0                      # HORIZONTAL field of view in degrees (verified from the matrix)
