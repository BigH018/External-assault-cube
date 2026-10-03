"""Tests for the custom widgets: toggle switch/row, segmented control, colour picker + colour chip."""

from __future__ import annotations

import pytest
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest

from actrainer.ui.widgets.colour_button import ColourButton
from actrainer.ui.widgets.colour_picker import ColourPopup, describe, from_qcolor, parse_hex, to_qcolor
from actrainer.ui.widgets.segmented import SegmentedControl
from actrainer.ui.widgets.toggle_switch import ToggleRow, ToggleSwitch


# --- toggle ---------------------------------------------------------------------------------

def test_toggle_switch_is_checkable_button(qapp) -> None:  # noqa: ANN001
    switch = ToggleSwitch()
    seen: list[bool] = []
    switch.toggled.connect(seen.append)
    switch.click()
    assert switch.isChecked() and seen == [True]


def test_toggle_row_label_click_toggles(qapp) -> None:  # noqa: ANN001
    row = ToggleRow("Enable", "desc")
    QTest.mouseClick(row, Qt.LeftButton, pos=QPoint(5, 5))
    assert row.switch.isChecked() and row.text() == "Enable"


# --- segmented ------------------------------------------------------------------------------

def test_segmented_selection(qapp) -> None:  # noqa: ANN001
    control = SegmentedControl(["A", "B", "C"])
    seen: list[int] = []
    control.currentIndexChanged.connect(seen.append)
    assert control.currentIndex() == 0
    control.buttons[2].click()
    assert control.currentIndex() == 2 and seen == [2]
    control.setCurrentIndex(1)                 # programmatic: no signal
    assert control.currentIndex() == 1 and seen == [2]


# --- colour helpers ---------------------------------------------------------------------------

def test_colour_round_trip_and_describe(qapp) -> None:  # noqa: ANN001
    assert from_qcolor(to_qcolor("#12345678")) == "#12345678"
    assert describe("#FF4040FF") == "#FF4040 · 100%"
    assert describe("#FF404080") == "#FF4040 · 50%"


@pytest.mark.parametrize("text, expected", [
    ("#ff0000", "#FF0000CC"), ("00ff00", "#00FF00CC"), ("#0000FF80", "#0000FF80"),
    (" #abcdef ", "#ABCDEFCC"), ("#xyz", None), ("#12345", None),
])
def test_parse_hex_keeps_alpha_when_missing(text: str, expected: str | None) -> None:
    assert parse_hex(text, alpha=0xCC) == expected


# --- popup ------------------------------------------------------------------------------------------

def test_popup_preset_keeps_opacity_and_previews(qapp) -> None:  # noqa: ANN001
    popup = ColourPopup("#FF404080")
    seen: list[str] = []
    popup.colourPreview.connect(seen.append)
    popup._apply_preset("#34C759")  # noqa: SLF001
    assert popup.current() == "#34C75980"
    assert seen[-1] == "#34C75980"


def test_popup_opacity_slider(qapp) -> None:  # noqa: ANN001
    popup = ColourPopup("#FFFFFFFF")
    popup.alpha_slider.setValue(50)
    assert popup.current().endswith("80") and popup.alpha_label.text() == "50%"


def test_popup_hex_entry(qapp) -> None:  # noqa: ANN001
    popup = ColourPopup("#FFFFFFFF")
    popup.hex_edit.setText("#336699")
    popup._on_hex()  # noqa: SLF001 - what editingFinished calls
    assert popup.current() == "#336699FF"
    popup.hex_edit.setText("nonsense")
    popup._on_hex()  # noqa: SLF001
    assert popup.current() == "#336699FF" and popup.hex_edit.text() == "#336699FF"  # rejected, value kept


# --- colour chip ----------------------------------------------------------------------------------

def test_colour_button_live_preview_and_cancel_restores(qapp) -> None:  # noqa: ANN001
    button = ColourButton("#FF4040FF")
    seen: list[str] = []
    button.colourChanged.connect(seen.append)
    button.open_picker()
    button.popup._apply_preset("#4C8DFF")  # noqa: SLF001 - user clicks a preset
    assert button.colour() == "#4C8DFFFF" and seen == ["#4C8DFFFF"]   # applied live
    button.popup.cancel()
    assert button.colour() == "#FF4040FF" and seen[-1] == "#FF4040FF"  # restored


def test_colour_button_apply_keeps_new_colour(qapp) -> None:  # noqa: ANN001
    button = ColourButton("#FF4040FF")
    button.open_picker()
    button.popup._apply_preset("#FFFFFF")  # noqa: SLF001
    button.popup.accept()
    assert button.colour() == "#FFFFFFFF"
    assert button.text() == "#FFFFFF · 100%"
