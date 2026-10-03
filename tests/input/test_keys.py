"""Tests for input/keys.py."""

from __future__ import annotations

from actrainer.input import keys


def test_names_round_trip_for_every_bindable_key() -> None:
    for vk in keys.BINDABLE_VKS:
        assert keys.vk_from_name(keys.key_name(vk)) == vk


def test_names_are_unique() -> None:
    assert len(set(keys.VK_TO_NAME.values())) == len(keys.VK_TO_NAME)


def test_common_names() -> None:
    assert keys.key_name(keys.VK_INSERT) == "INSERT"
    assert keys.key_name(keys.VK_END) == "END"
    assert keys.key_name(keys.VK_RBUTTON) == "RMB"
    assert keys.vk_from_name("f5") == 0x74
    assert keys.vk_from_name("mouse4") == 0x05


def test_unbound_and_unknown() -> None:
    assert keys.key_name(None) == keys.UNBOUND_NAME
    assert keys.key_name(0xFF) == "VK 0xFF"
    assert keys.vk_from_name(None) is None
    assert keys.vk_from_name("") is None
    assert keys.vk_from_name("Unbound") is None
    assert keys.vk_from_name("NOT_A_KEY") is None


def test_escape_and_generic_modifiers_are_not_bindable() -> None:
    assert keys.VK_ESCAPE not in keys.BINDABLE_VKS     # Escape clears a bind
    for generic in (0x10, 0x11, 0x12):                 # Shift/Ctrl/Alt: use L/R variants
        assert generic not in keys.BINDABLE_VKS
