"""Aimbot tab: enable + activation key, targeting, FOV (+ circle), smoothing, team check, max distance."""

from __future__ import annotations

from PyQt5.QtWidgets import QVBoxLayout, QWidget

from actrainer.input.actions import AIMBOT_ACTIVATE
from actrainer.settings.models import AimTarget, Settings, TargetPriority
from actrainer.settings.signals import AppSignals
from actrainer.ui.binder import KeybindBinder, SettingBinder
from actrainer.ui.layout import group, hint, labelled, row

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
        a.addWidget(b.checkbox("enabled", "Enable aimbot"))
        a.addWidget(labelled("Key", row(self.keys.button(AIMBOT_ACTIVATE), self.keys.mode_combo(AIMBOT_ACTIVATE),
                                        stretch_last=True)))
        a.addWidget(hint("Hold: aims only while the key is held. Toggle: each press turns aiming on/off."))

        targeting, t = group("Targeting")
        t.addWidget(labelled("Aim at", b.combo("target", TARGET_LABELS)))
        t.addWidget(labelled("Priority", b.combo("priority", PRIORITY_LABELS)))
        t.addWidget(b.slider("max_distance", "Max distance", suffix=" u"))
        t.addWidget(b.checkbox("team_check", "Team check (ignore teammates)",
                               "Leave OFF in free-for-all modes: bots there still have team values, "
                               "and some share yours."))
        t.addWidget(hint("Dead players are always ignored. Distance is in world units (eye height ≈ 4.5 u)."))

        fov, f = group("Field of view")
        f.addWidget(b.slider("fov_deg", "FOV radius", decimals=1, suffix="°"))
        f.addWidget(row(b.checkbox("draw_fov", "Draw FOV circle"), b.colour("fov_colour"), stretch_last=True))
        f.addWidget(b.slider("fov_thickness", "Circle thickness", suffix=" px"))
        f.addWidget(hint("Only targets within this angle of your crosshair are considered."))

        smoothing, s = group("Smoothing")
        s.addWidget(b.slider("smoothing", "Smoothing", decimals=1))
        s.addWidget(hint("1 = instant snap. Higher = smoother and slower. Each tick moves 1/smoothing of the way."))

        layout = QVBoxLayout(self)
        for box in (activation, targeting, fov, smoothing):
            layout.addWidget(box)
        layout.addStretch(1)

    def load_from_settings(self) -> None:
        self.binder.load()
        self.keys.load()
