"""ESP tab: enable + toggle key, styles (combinable), line thickness, colours, extras."""

from __future__ import annotations

from PyQt5.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from actrainer.input.actions import ESP_TOGGLE
from actrainer.settings.models import Settings, SnaplineOrigin
from actrainer.settings.signals import AppSignals
from actrainer.ui.binder import KeybindBinder, SettingBinder
from actrainer.ui.layout import group, hint, labelled, row

SNAPLINE_LABELS = {SnaplineOrigin.BOTTOM: "Screen bottom", SnaplineOrigin.CENTRE: "Screen centre"}


class EspTab(QWidget):
    def __init__(self, settings: Settings, signals: AppSignals) -> None:
        super().__init__()
        self.binder = SettingBinder(settings, signals, "esp")
        self.keys = KeybindBinder(settings, signals)
        b = self.binder

        general, g = group("General")
        g.addWidget(row(b.checkbox("enabled", "Enable ESP"), None,
                        QLabel("Toggle key"), self.keys.button(ESP_TOGGLE)))
        g.addWidget(b.checkbox("enemies_only", "Enemies only"))

        styles, s = group("Styles (combine freely)")
        s.addWidget(row(b.checkbox("box_2d", "2D box"), b.checkbox("corner_box", "Corner box"),
                        b.checkbox("head_circle", "Head circle"), b.checkbox("skeleton", "Skeleton"),
                        stretch_last=True))
        s.addWidget(b.slider("thickness", "Line thickness", suffix=" px"))
        colours = QGridLayout()
        colours.addWidget(QLabel("Enemies"), 0, 0)
        colours.addWidget(b.colour("enemy_colour"), 0, 1)
        colours.addWidget(QLabel("Teammates"), 0, 2)
        colours.addWidget(b.colour("team_colour"), 0, 3)
        colours.setColumnStretch(4, 1)
        s.addLayout(colours)
        s.addWidget(hint("Skeleton is approximate: the game stores no bones, so it's built from head, feet and facing."))

        extras, e = group("Extras")
        e.addWidget(row(b.checkbox("show_name", "Name"), b.checkbox("show_distance", "Distance"),
                        b.checkbox("show_health_bar", "Health bar"),
                        b.checkbox("show_health_number", "Health number"), stretch_last=True))
        e.addWidget(row(b.checkbox("show_snaplines", "Snaplines"),
                        labelled("from", b.combo("snapline_origin", SNAPLINE_LABELS), label_width=30),
                        stretch_last=True))

        layout = QVBoxLayout(self)
        for box in (general, styles, extras):
            layout.addWidget(box)
        layout.addStretch(1)

    def load_from_settings(self) -> None:
        self.binder.load()
        self.keys.load()
