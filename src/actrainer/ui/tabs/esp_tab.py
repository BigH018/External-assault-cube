"""ESP page: enable + toggle key, teams, styles (combinable chips), colours, info extras."""

from __future__ import annotations

from PyQt5.QtWidgets import QVBoxLayout, QWidget

from actrainer.input.actions import ESP_TOGGLE
from actrainer.settings.models import Settings, SnaplineOrigin
from actrainer.settings.signals import AppSignals
from actrainer.ui.binder import KeybindBinder, SettingBinder
from actrainer.ui.layout import group, hint, labelled, row

TITLE = "ESP"
SUBTITLE = "Draws boxes, skeletons and info over bots, even through walls."

SNAPLINE_LABELS = {SnaplineOrigin.BOTTOM: "Screen bottom", SnaplineOrigin.CENTRE: "Screen centre"}


class EspTab(QWidget):
    def __init__(self, settings: Settings, signals: AppSignals) -> None:
        super().__init__()
        self.binder = SettingBinder(settings, signals, "esp")
        self.keys = KeybindBinder(settings, signals)
        b = self.binder

        general, g = group("General")
        g.addWidget(b.toggle("enabled", "Enable ESP"))
        g.addWidget(labelled("Toggle key", self.keys.button(ESP_TOGGLE)))
        g.addWidget(b.toggle("team_mode", "Team mode", "Use team colours. Leave OFF in free-for-all, where every bot "
                                                       "is an enemy."))
        g.addWidget(b.toggle("enemies_only", "Enemies only", "Hide teammates (team mode only)."))

        style, s = group("Style")
        s.addWidget(labelled("Draw", row(b.chip("box_2d", "2D box"), b.chip("corner_box", "Corner box"),
                                         b.chip("head_circle", "Head circle"), b.chip("skeleton", "Skeleton"),
                                         stretch_last=True)))
        s.addWidget(hint("Pick any combination. The skeleton is approximate: the game stores no bones."))
        s.addWidget(b.slider("thickness", "Line thickness", suffix=" px"))
        s.addWidget(labelled("Enemy colour", b.colour("enemy_colour")))
        s.addWidget(labelled("Team colour", b.colour("team_colour")))

        info, i = group("Info")
        i.addWidget(labelled("Show", row(b.chip("show_name", "Name"), b.chip("show_distance", "Distance"),
                                         b.chip("show_health_bar", "Health bar"),
                                         b.chip("show_health_number", "Health number"), stretch_last=True)))
        i.addWidget(b.toggle("show_snaplines", "Snaplines", "A line from the screen to each bot."))
        i.addWidget(labelled("Snaplines from", b.segmented("snapline_origin", SNAPLINE_LABELS)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for box in (general, style, info):
            layout.addWidget(box)
        layout.addStretch(1)

    def load_from_settings(self) -> None:
        self.binder.load()
        self.keys.load()
