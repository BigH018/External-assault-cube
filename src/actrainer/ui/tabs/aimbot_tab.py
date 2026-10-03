"""Aimbot page: enable + activation key, targeting, FOV (+ circle), smoothing."""

from __future__ import annotations

from PyQt5.QtWidgets import QVBoxLayout, QWidget

from actrainer.input.actions import AIMBOT_ACTIVATE
from actrainer.settings.models import AimTarget, Settings, TargetPriority
from actrainer.settings.signals import AppSignals
from actrainer.ui.binder import KeybindBinder, SettingBinder
from actrainer.ui.layout import group, hint, labelled, row

TITLE = "Aimbot"
SUBTITLE = "Automatically aims at bots near your crosshair while the activation key is active."

TARGET_LABELS = {AimTarget.HEAD: "Head", AimTarget.BODY: "Body"}
PRIORITY_LABELS = {
    TargetPriority.CROSSHAIR: "Closest to crosshair",
    TargetPriority.DISTANCE: "Closest distance",
    TargetPriority.HEALTH: "Lowest health",
}


class AimbotTab(QWidget):
    def __init__(self, settings: Settings, signals: AppSignals) -> None:
        super().__init__()
        self.binder = SettingBinder(settings, signals, "aimbot")
        self.keys = KeybindBinder(settings, signals)
        b = self.binder

        activation, a = group("Activation")
        a.addWidget(b.toggle("enabled", "Enable aimbot", "Only aims while the game window is focused."))
        a.addWidget(labelled("Activation key", row(self.keys.button(AIMBOT_ACTIVATE),
                                                   self.keys.mode_segmented(AIMBOT_ACTIVATE), stretch_last=True)))
        a.addWidget(hint("Hold: aims while the key is held. Toggle: one press turns aiming on, the next turns it off."))

        targeting, t = group("Targeting")
        t.addWidget(labelled("Aim at", b.segmented("target", TARGET_LABELS)))
        t.addWidget(labelled("Priority", b.segmented("priority", PRIORITY_LABELS)))
        t.addWidget(b.slider("max_distance", "Max distance", suffix=" u"))
        t.addWidget(b.toggle("team_check", "Team check", "Ignore teammates. Leave OFF in free-for-all: FFA bots "
                                                         "still carry team values and some share yours."))
        t.addWidget(hint("Dead players are always ignored. Distance is in world units (eye height ≈ 4.5 u)."))

        fov, f = group("Field of view")
        f.addWidget(b.slider("fov_deg", "FOV radius", decimals=1, suffix="°"))
        f.addWidget(hint("Only bots within this angle of your crosshair are targeted."))
        f.addWidget(b.toggle("draw_fov", "Draw FOV circle", "Shows the radius on the overlay while the aimbot is enabled."))
        f.addWidget(labelled("Circle colour", b.colour("fov_colour")))
        f.addWidget(b.slider("fov_thickness", "Circle thickness", suffix=" px"))

        smoothing, s = group("Smoothing")
        s.addWidget(b.slider("smoothing", "Smoothing", decimals=1))
        s.addWidget(hint("1 = instant snap. Higher = smoother and slower (each tick covers 1/smoothing of the way)."))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for box in (activation, targeting, fov, smoothing):
            layout.addWidget(box)
        layout.addStretch(1)

    def load_from_settings(self) -> None:
        self.binder.load()
        self.keys.load()
