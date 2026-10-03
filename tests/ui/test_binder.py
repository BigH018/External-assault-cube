"""Tests for ui/binder.py: controls write settings, emit changes and reload after replace_with."""

from __future__ import annotations

from actrainer import config
from actrainer.input.actions import AIMBOT_ACTIVATE, BindMode
from actrainer.settings.models import AimTarget, Settings
from actrainer.settings.signals import AppSignals
from actrainer.settings.store import default_settings
from actrainer.ui.binder import KeybindBinder, SettingBinder


def collect(signals: AppSignals) -> list[str]:
    seen: list[str] = []
    signals.settings_changed.connect(seen.append)
    return seen


def test_toggle_writes_setting_and_emits(settings: Settings, signals: AppSignals) -> None:
    seen = collect(signals)
    row = SettingBinder(settings, signals, "aimbot").toggle("enabled", "Enable")
    row.switch.setChecked(True)
    assert settings.aimbot.enabled is True
    assert seen == ["aimbot"]


def test_slider_uses_field_range_and_types(settings: Settings, signals: AppSignals) -> None:
    b = SettingBinder(settings, signals, "aimbot")
    fov = b.slider("fov_deg", "FOV", decimals=1)
    thickness = b.slider("fov_thickness", "Thickness")
    fov._slider.setValue(fov._slider.maximum())  # noqa: SLF001 - simulate dragging to the end
    thickness._slider.setValue(3)  # noqa: SLF001
    assert settings.aimbot.fov_deg == config.AIM_FOV_RANGE[1]
    assert settings.aimbot.fov_thickness == 3 and isinstance(settings.aimbot.fov_thickness, int)


def test_combo_writes_enum(settings: Settings, signals: AppSignals) -> None:
    combo = SettingBinder(settings, signals, "aimbot").combo("target", {AimTarget.HEAD: "Head", AimTarget.BODY: "Body"})
    combo.setCurrentIndex(1)
    assert settings.aimbot.target is AimTarget.BODY


def test_load_refreshes_after_profile_replace_without_emitting(settings: Settings, signals: AppSignals) -> None:
    b = SettingBinder(settings, signals, "aimbot")
    row = b.toggle("enabled", "Enable")
    fov = b.slider("fov_deg", "FOV", decimals=1)
    other = default_settings()
    other.aimbot.enabled = True
    other.aimbot.fov_deg = 42.0
    settings.replace_with(other)
    seen = collect(signals)
    b.load()
    assert row.switch.isChecked() and fov.value() == 42.0
    assert seen == []  # loading must not mark the profile dirty


def test_binder_writes_to_current_section_after_replace(settings: Settings, signals: AppSignals) -> None:
    row = SettingBinder(settings, signals, "aimbot").toggle("enabled", "Enable")
    settings.replace_with(default_settings())  # section object replaced
    row.switch.setChecked(True)
    assert settings.aimbot.enabled is True     # wrote to the NEW section, not a stale one


def test_keybind_binder_mode_and_key(settings: Settings, signals: AppSignals) -> None:
    seen = collect(signals)
    kb = KeybindBinder(settings, signals)
    combo = kb.mode_combo(AIMBOT_ACTIVATE)
    button = kb.button(AIMBOT_ACTIVATE)
    combo.setCurrentIndex(1)  # Hold -> Toggle
    button.keyChanged.emit(0x46)  # what a finished capture emits
    assert settings.keybinds.binds[AIMBOT_ACTIVATE].mode is BindMode.TOGGLE
    assert settings.keybinds.binds[AIMBOT_ACTIVATE].key == 0x46
    assert seen == ["keybinds", "keybinds"]


def test_keybind_capture_signals_forwarded(settings: Settings, signals: AppSignals) -> None:
    states: list[bool] = []
    signals.bind_capture_changed.connect(states.append)
    button = KeybindBinder(settings, signals).button(AIMBOT_ACTIVATE)
    button.captureStarted.emit()
    button.captureFinished.emit()
    assert states == [True, False]


def test_chip_writes_bool(settings: Settings, signals: AppSignals) -> None:
    chip = SettingBinder(settings, signals, "esp").chip("skeleton", "Skeleton")
    assert chip.isCheckable() and not chip.isChecked()
    chip.setChecked(True)
    assert settings.esp.skeleton is True


def test_segmented_writes_enum_and_reloads(settings: Settings, signals: AppSignals) -> None:
    b = SettingBinder(settings, signals, "aimbot")
    control = b.segmented("target", {AimTarget.HEAD: "Head", AimTarget.BODY: "Body"})
    control.buttons[1].click()
    assert settings.aimbot.target is AimTarget.BODY
    settings.aimbot.target = AimTarget.HEAD
    b.load()
    assert control.currentIndex() == 0


def test_keybind_mode_segmented(settings: Settings, signals: AppSignals) -> None:
    control = KeybindBinder(settings, signals).mode_segmented(AIMBOT_ACTIVATE)
    control.buttons[1].click()  # Toggle
    assert settings.keybinds.binds[AIMBOT_ACTIVATE].mode is BindMode.TOGGLE
