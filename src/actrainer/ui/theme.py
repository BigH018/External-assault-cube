"""Dark theme: colour palette, fonts and the application stylesheet.

All UI colours live here. Tabs and widgets refer to these names (or to object names / dynamic
properties styled below), never to inline hex values.
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

BG = "#14161B"           # window background
SURFACE = "#1C1F26"      # group boxes, inputs
SURFACE_HIGH = "#252932" # hover / raised
BORDER = "#2E333D"
TEXT = "#E6E8EC"
TEXT_DIM = "#8B92A0"
ACCENT = "#4C8DFF"
ACCENT_HOVER = "#6AA1FF"
OK = "#3FCF8E"
WARN = "#F0B429"
DANGER = "#F25F5C"

# Qt stylesheets need forward slashes in url() paths, even on Windows.
_ASSETS = Path(__file__).resolve().parent / "assets"
ARROW_UP = (_ASSETS / "arrow_up.svg").as_posix()
ARROW_DOWN = (_ASSETS / "arrow_down.svg").as_posix()

FONT_FAMILY = "Segoe UI"
FONT_SIZE_PT = 10

STYLESHEET = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "{FONT_FAMILY}";
    font-size: {FONT_SIZE_PT}pt;
}}
QToolTip {{ background: {SURFACE_HIGH}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}

QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 6px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {TEXT_DIM};
    padding: 8px 16px; margin-right: 2px; border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QGroupBox {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px;
    margin-top: 14px; padding: 12px 10px 8px 10px; font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {TEXT_DIM}; }}
QGroupBox QWidget {{ background: {SURFACE}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; border: none; }}

QPushButton {{
    background: {SURFACE_HIGH}; border: 1px solid {BORDER}; border-radius: 4px; padding: 5px 12px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: {SURFACE_HIGH}; border-color: {BORDER}; color: {TEXT_DIM}; }}
QPushButton#danger {{ border-color: {DANGER}; color: {DANGER}; }}
QPushButton#danger:hover {{ background: {DANGER}; color: white; }}
QPushButton#keybind {{ min-width: 90px; font-family: Consolas, monospace; }}
QPushButton#keybind[capturing="true"] {{ border-color: {WARN}; color: {WARN}; }}
QPushButton#keybind[conflict="true"] {{ border-color: {DANGER}; color: {DANGER}; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {BORDER}; border-radius: 3px; background: {BG};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QListWidget {{
    background: {BG}; border: 1px solid {BORDER}; border-radius: 4px; padding: 4px 6px;
    selection-background-color: {ACCENT};
}}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{ border-color: {ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 16px; background: {SURFACE_HIGH}; border-left: 1px solid {BORDER};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{ARROW_UP}"); width: 8px; height: 5px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{ARROW_DOWN}"); width: 8px; height: 5px; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox::down-arrow {{ image: url("{ARROW_DOWN}"); width: 8px; height: 5px; margin-right: 6px; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; border: 1px solid {BORDER}; }}
QListWidget::item {{ padding: 4px; }}
QListWidget::item:selected {{ background: {ACCENT}; color: white; }}

QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {TEXT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT_HOVER}; }}

QLabel#dim {{ color: {TEXT_DIM}; }}
QLabel#value {{ color: {TEXT_DIM}; font-family: Consolas, monospace; min-width: 56px; }}
QLabel#warning {{ color: {WARN}; }}
QLabel#danger {{ color: {DANGER}; }}
QLabel#status[state="ok"] {{ color: {OK}; font-weight: 600; }}
QLabel#status[state="warn"] {{ color: {WARN}; font-weight: 600; }}
QLabel#status[state="bad"] {{ color: {DANGER}; font-weight: 600; }}
QLabel#title {{ font-size: 13pt; font-weight: 600; }}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the dark stylesheet and default font to the whole application."""
    app.setFont(QFont(FONT_FAMILY, FONT_SIZE_PT))
    app.setStyleSheet(STYLESHEET)


def restyle(widget: object) -> None:
    """Re-apply the stylesheet after changing a dynamic property (e.g. capturing / conflict / state)."""
    style = widget.style()  # type: ignore[attr-defined]
    style.unpolish(widget)
    style.polish(widget)
