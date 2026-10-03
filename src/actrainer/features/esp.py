"""ESP: turn a GameState + settings into draw primitives. Pure: no Qt, no memory.

For each live bot (furthest first, so nearer ones draw on top):
  1. project feet and the top of the head to screen pixels; skip the bot if either is behind the camera
  2. derive a 2D box from those two points (height from the projection, width from a body aspect ratio)
  3. add the enabled styles (2D box, corner box, head circle, skeleton) and extras (name, health bar,
     health number, distance, snapline)
Plus the aimbot FOV circle when the aimbot is enabled and "draw FOV circle" is on.
"""

from __future__ import annotations

from dataclasses import dataclass

from actrainer.game.structs import GameState, PlayerSnapshot, Vec3
from actrainer.maths import vectors
from actrainer.maths.projection import fov_circle_radius, world_to_screen
from actrainer.maths.skeleton import build_skeleton
from actrainer.settings.models import AimbotSettings, EspSettings, SnaplineOrigin
from actrainer.features.primitives import Circle, FilledRect, Line, Primitive, Rect, Text, TextAlign

# --- tuning constants (world units / fractions of the box) ---------------------------------
HEAD_TOP_EXTRA = 0.8          # head pos is the EYE; the top of the head is about this much higher (world units)
BOX_ASPECT = 0.45             # box width = height * this (a standing player is roughly 2.2x taller than wide)
CORNER_FRACTION = 0.25        # corner box: each corner line covers this fraction of the side
HEAD_RADIUS_FRACTION = 0.09   # head circle radius = box height * this
HEALTH_BAR_WIDTH = 3.0        # pixels
HEALTH_BAR_GAP = 3.0          # pixels between the bar and the box
TEXT_GAP = 2.0                # pixels between the box and the text
TEXT_SIZE_PX = 12
MAX_HEALTH = 100
OFFSCREEN_MARGIN = 2.0        # skip bots whose box lies further than this many screen sizes off-screen
TARGET_EXTRA_THICKNESS = 1.0  # the aimbot's current target is outlined thicker

HEALTH_FULL = (0x34, 0xC7, 0x59)   # green
HEALTH_EMPTY = (0xFF, 0x3B, 0x30)  # red
HEALTH_BG = "#000000A0"
TEXT_COLOUR = "#FFFFFFFF"


@dataclass(frozen=True, slots=True)
class ScreenBox:
    """A bot's on-screen bounding box."""

    x: float
    y: float
    w: float
    h: float

    @property
    def centre_x(self) -> float:
        return self.x + self.w / 2

    @property
    def bottom(self) -> float:
        return self.y + self.h


def health_colour(health: int) -> str:
    """Green at full health fading to red at zero."""
    t = max(0.0, min(1.0, health / MAX_HEALTH))
    r, g, b = (round(e + (f - e) * t) for e, f in zip(HEALTH_EMPTY, HEALTH_FULL))
    return f"#{r:02X}{g:02X}{b:02X}FF"


def screen_box(player: PlayerSnapshot, matrix: tuple[float, ...], width: float, height: float) -> ScreenBox | None:
    """Project a player to a 2D box, or None if they're behind the camera or far off-screen."""
    top = world_to_screen(Vec3(player.head.x, player.head.y, player.head.z + HEAD_TOP_EXTRA), matrix, width, height)
    feet = world_to_screen(player.feet, matrix, width, height)
    if top is None or feet is None:
        return None
    h = feet[1] - top[1]
    if h <= 0:
        return None  # degenerate (e.g. looking straight down onto them)
    w = h * BOX_ASPECT
    cx = (top[0] + feet[0]) / 2
    box = ScreenBox(cx - w / 2, top[1], w, h)
    if (box.x > width * (1 + OFFSCREEN_MARGIN) or box.x + box.w < -width * OFFSCREEN_MARGIN
            or box.y > height * (1 + OFFSCREEN_MARGIN) or box.bottom < -height * OFFSCREEN_MARGIN):
        return None
    return box


def _corner_box(box: ScreenBox, colour: str, t: float) -> list[Primitive]:
    cw, ch = box.w * CORNER_FRACTION, box.h * CORNER_FRACTION
    x0, y0, x1, y1 = box.x, box.y, box.x + box.w, box.bottom
    return [
        Line(x0, y0, x0 + cw, y0, colour, t), Line(x0, y0, x0, y0 + ch, colour, t),   # top-left
        Line(x1, y0, x1 - cw, y0, colour, t), Line(x1, y0, x1, y0 + ch, colour, t),   # top-right
        Line(x0, y1, x0 + cw, y1, colour, t), Line(x0, y1, x0, y1 - ch, colour, t),   # bottom-left
        Line(x1, y1, x1 - cw, y1, colour, t), Line(x1, y1, x1, y1 - ch, colour, t),   # bottom-right
    ]


def _skeleton(player: PlayerSnapshot, matrix: tuple[float, ...], width: float, height: float,
              colour: str, t: float) -> list[Primitive]:
    lines: list[Primitive] = []
    for start, end in build_skeleton(player.head, player.feet, player.yaw).bone_segments():
        a = world_to_screen(start, matrix, width, height)
        b = world_to_screen(end, matrix, width, height)
        if a is not None and b is not None:
            lines.append(Line(a[0], a[1], b[0], b[1], colour, t))
    return lines


def _health_bar(box: ScreenBox, health: int) -> list[Primitive]:
    fraction = max(0.0, min(1.0, health / MAX_HEALTH))
    x = box.x - HEALTH_BAR_GAP - HEALTH_BAR_WIDTH
    filled = box.h * fraction
    return [FilledRect(x, box.y, HEALTH_BAR_WIDTH, box.h, HEALTH_BG),
            FilledRect(x, box.bottom - filled, HEALTH_BAR_WIDTH, filled, health_colour(health))]


def build_player(player: PlayerSnapshot, local: PlayerSnapshot, state: GameState, esp: EspSettings,
                 width: float, height: float, is_target: bool = False) -> list[Primitive]:
    """All primitives for one bot (empty if it isn't drawable)."""
    teammate = esp.team_mode and player.team == local.team
    if teammate and esp.enemies_only:
        return []
    box = screen_box(player, state.view_matrix, width, height)
    if box is None:
        return []
    colour = esp.team_colour if teammate else esp.enemy_colour
    t = esp.thickness + (TARGET_EXTRA_THICKNESS if is_target else 0)
    out: list[Primitive] = []

    if esp.show_snaplines:
        origin_y = height if esp.snapline_origin is SnaplineOrigin.BOTTOM else height / 2
        out.append(Line(width / 2, origin_y, box.centre_x, box.bottom, colour, esp.thickness))
    if esp.box_2d:
        out.append(Rect(box.x, box.y, box.w, box.h, colour, t))
    if esp.corner_box:
        out.extend(_corner_box(box, colour, t))
    if esp.skeleton:
        out.extend(_skeleton(player, state.view_matrix, width, height, colour, t))
    if esp.head_circle:
        head = world_to_screen(player.head, state.view_matrix, width, height)
        if head is not None:
            out.append(Circle(head[0], head[1], max(1.0, box.h * HEAD_RADIUS_FRACTION), colour, t))
    if esp.show_health_bar:
        out.extend(_health_bar(box, player.health))

    # Text: name above the box; health number / distance below it.
    if esp.show_name and player.name:
        out.append(Text(box.centre_x, box.y - TEXT_GAP - TEXT_SIZE_PX - 2, player.name, TEXT_COLOUR, TEXT_SIZE_PX))
    below: list[str] = []
    if esp.show_health_number:
        below.append(f"{player.health} hp")
    if esp.show_distance:
        below.append(f"{vectors.distance(local.head, player.head):.0f} u")
    if below:
        out.append(Text(box.centre_x, box.bottom + TEXT_GAP, " · ".join(below), TEXT_COLOUR, TEXT_SIZE_PX))
    return out


def build_fov_circle(state: GameState, aimbot: AimbotSettings, width: float, height: float) -> list[Primitive]:
    """The aimbot FOV circle at the screen centre (only when the aimbot is enabled and drawing is on)."""
    if not (aimbot.enabled and aimbot.draw_fov) or state.fov <= 0:
        return []
    radius = fov_circle_radius(aimbot.fov_deg, state.fov, width)
    return [Circle(width / 2, height / 2, radius, aimbot.fov_colour, aimbot.fov_thickness)]


def build_esp(state: GameState, esp: EspSettings, aimbot: AimbotSettings, width: float, height: float,
              aim_target_address: int | None = None) -> list[Primitive]:
    """Every primitive for one overlay frame."""
    out: list[Primitive] = []
    if esp.enabled and len(state.view_matrix) == 16:
        local = state.local
        # Furthest first, so nearer players are drawn on top.
        for player in sorted(state.entities, key=lambda p: -vectors.distance(local.head, p.head)):
            out.extend(build_player(player, local, state, esp, width, height,
                                    is_target=player.address == aim_target_address))
    out.extend(build_fov_circle(state, aimbot, width, height))
    return out
