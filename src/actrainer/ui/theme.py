"""Theme: colour palette, fonts, asset paths and the application stylesheet.

All UI colours live here. Tabs and widgets refer to these names (or to object names / dynamic
properties styled below), never to inline hex values. Accent: ice blue, to match the logo.
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QApplication

# --- palette ---------------------------------------------------------------------------
BG = "#0F1115"            # window background
SIDEBAR = "#12151B"       # navigation column + header
SURFACE = "#171A21"       # cards
SURFACE_HIGH = "#20242D"  # inputs, buttons, hover
BORDER = "#2A2F3A"
TEXT = "#E8ECF2"
TEXT_DIM = "#8A93A3"
ACCENT = "#8EC9FF"        # ice blue
ACCENT_HOVER = "#B5DCFF"
ACCENT_TEXT = "#0B1520"   # text drawn ON the accent colour (dark, for contrast)
ACCENT_SOFT = "#1E2E40"   # selected nav item background
OK = "#3FCF8E"
WARN = "#F0B429"
DANGER = "#F25F5C"
SWITCH_OFF = "#3A404D"
KNOB = "#FFFFFF"

FONT_FAMILY = "Segoe UI"
FONT_SIZE_PT = 10

# --- assets -----------------------------------------------------------------------------
# Qt stylesheets need forward slashes in url() paths, even on Windows.
ASSETS = Path(__file__).resolve().parent / "assets"
ARROW_UP = (ASSETS / "arrow_up.svg").as_posix()
ARROW_DOWN = (ASSETS / "arrow_down.svg").as_posix()
LOGO_PNG = ASSETS / "logo.png"   # 256 px, made from docs/assets/logo-source.jpg (1920 px artwork)
LOGO_ICO = ASSETS / "logo.ico"   # the original 32 px icon (kept for shortcuts; the app uses the PNG)

STYLESHEET = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "{FONT_FAMILY}";
    font-size: {FONT_SIZE_PT}pt;
}}
QToolTip {{ background: {SURFACE_HIGH}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px; border-radius: 4px; }}

/* ---- header + sidebar ---- */
QWidget#header {{ background: {SIDEBAR}; border-bottom: 1px solid {BORDER}; }}
QWidget#header QLabel {{ background: transparent; }}
QLabel#appTitle {{ font-size: 15pt; font-weight: 700; }}
QLabel#appSubtitle {{ color: {ACCENT}; font-size: 10pt; font-weight: 600; }}
QWidget#sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
QWidget#sidebar QLabel {{ background: transparent; }}
QPushButton#nav {{
    background: transparent; border: none; border-radius: 8px;
    text-align: left; padding: 9px 12px; color: {TEXT_DIM}; font-size: 10.5pt;
}}
QPushButton#nav:hover {{ background: {SURFACE_HIGH}; color: {TEXT}; }}
QPushButton#nav:checked {{ background: {ACCENT_SOFT}; color: {ACCENT}; font-weight: 600; }}

/* ---- page header ---- */
QLabel#pageTitle {{ font-size: 16pt; font-weight: 700; }}
QLabel#pageSubtitle {{ color: {TEXT_DIM}; }}

/* ---- cards ---- */
QGroupBox {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
    margin-top: 0px; padding: 38px 14px 12px 14px; font-weight: 600; font-size: 10.5pt;
}}
QGroupBox::title {{
    subcontrol-origin: padding; subcontrol-position: top left; left: 14px; top: 11px; color: {TEXT};
}}
QGroupBox QWidget {{ background: {SURFACE}; font-weight: normal; font-size: {FONT_SIZE_PT}pt; }}
/* "QGroupBox QWidget" outranks plain type selectors, so controls inside cards need their own background again. */
QGroupBox QPushButton, QGroupBox QComboBox, QGroupBox QSpinBox, QGroupBox QLineEdit, QGroupBox QListWidget,
QFrame#colourPopup QPushButton, QFrame#colourPopup QLineEdit {{ background: {SURFACE_HIGH}; }}
QGroupBox QPushButton#primary, QFrame#colourPopup QPushButton#primary {{ background: {ACCENT}; color: {ACCENT_TEXT}; }}
QGroupBox QPushButton#primary:hover, QFrame#colourPopup QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QGroupBox QPushButton#primary:disabled {{ background: {SURFACE_HIGH}; color: {TEXT_DIM}; }}
QGroupBox QPushButton#danger {{ background: transparent; }}
QGroupBox QPushButton#danger:hover {{ background: {DANGER}; color: white; }}
QGroupBox QPushButton#chip:checked, QGroupBox QPushButton#segment:checked {{ background: {ACCENT}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {SWITCH_OFF}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---- buttons ---- */
QPushButton {{
    background: {SURFACE_HIGH}; border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 14px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER}; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: {ACCENT_TEXT}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: {SURFACE_HIGH}; border-color: {BORDER}; color: {TEXT_DIM}; }}
QPushButton#danger {{ border-color: {DANGER}; color: {DANGER}; background: transparent; }}
QPushButton#danger:hover {{ background: {DANGER}; color: white; }}
QPushButton#keybind {{ min-width: 96px; font-family: Consolas, monospace; }}
QPushButton#keybind[capturing="true"] {{ border-color: {WARN}; color: {WARN}; }}
QPushButton#keybind[conflict="true"] {{ border-color: {DANGER}; color: {DANGER}; }}

/* chips: multi-select toggles (ESP styles / extras) */
QPushButton#chip {{
    background: {SURFACE_HIGH}; border: 1px solid {BORDER}; border-radius: 14px; padding: 5px 14px; color: {TEXT_DIM};
}}
QPushButton#chip:hover {{ border-color: {ACCENT}; color: {TEXT}; }}
QPushButton#chip:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: {ACCENT_TEXT}; }}

/* segmented control: one-of-N choice */
QPushButton#segment {{
    background: {SURFACE_HIGH}; border: 1px solid {BORDER}; border-radius: 0; padding: 5px 14px; color: {TEXT_DIM};
}}
QPushButton#segment[first="true"] {{ border-top-left-radius: 6px; border-bottom-left-radius: 6px; }}
QPushButton#segment[last="true"] {{ border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
QPushButton#segment:hover {{ color: {TEXT}; }}
QPushButton#segment:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: {ACCENT_TEXT}; }}

/* colour chip button (swatch is painted by the widget itself) */
QPushButton#colourChip {{ text-align: left; padding: 5px 12px 5px 38px; font-family: Consolas, monospace; }}

/* ---- inputs ---- */
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QListWidget {{
    background: {SURFACE_HIGH}; border: 1px solid {BORDER}; border-radius: 6px; padding: 4px 8px;
    selection-background-color: {ACCENT}; selection-color: {ACCENT_TEXT};
}}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover, QLineEdit:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 16px; background: {SURFACE_HIGH}; border-left: 1px solid {BORDER};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{ARROW_UP}"); width: 8px; height: 5px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{ARROW_DOWN}"); width: 8px; height: 5px; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox::down-arrow {{ image: url("{ARROW_DOWN}"); width: 8px; height: 5px; margin-right: 6px; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; border: 1px solid {BORDER}; selection-background-color: {ACCENT_SOFT}; }}
QListWidget::item {{ padding: 6px; border-radius: 4px; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}

QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {KNOB}; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT_HOVER}; }}

/* ---- labels ---- */
QLabel#dim {{ color: {TEXT_DIM}; }}
QLabel#value {{ color: {ACCENT}; font-family: Consolas, monospace; min-width: 60px; }}
QLabel#warning {{ color: {WARN}; }}
QLabel#danger {{ color: {DANGER}; }}
QLabel#status[state="ok"] {{ color: {OK}; font-weight: 600; }}
QLabel#status[state="warn"] {{ color: {WARN}; font-weight: 600; }}
QLabel#status[state="bad"] {{ color: {DANGER}; font-weight: 600; }}
QLabel#pill {{ border-radius: 12px; padding: 4px 12px; font-weight: 600; background: {SURFACE_HIGH}; }}
QLabel#pill[state="ok"] {{ color: {OK}; }}
QLabel#pill[state="warn"] {{ color: {WARN}; }}
QLabel#pill[state="bad"] {{ color: {DANGER}; }}

/* ---- colour picker popup ---- */
QFrame#colourPopup {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#colourPopup QWidget {{ background: {SURFACE}; }}
QPushButton#swatch {{ border: 1px solid {BORDER}; border-radius: 6px; padding: 0; min-width: 22px; min-height: 22px; }}
QPushButton#swatch:hover {{ border: 2px solid {TEXT}; }}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the dark stylesheet, default font and the logo as the app/window icon."""
    app.setFont(QFont(FONT_FAMILY, FONT_SIZE_PT))
    app.setStyleSheet(STYLESHEET)
    if LOGO_PNG.is_file():
        app.setWindowIcon(QIcon(str(LOGO_PNG)))


def restyle(widget: object) -> None:
    """Re-apply the stylesheet after changing a dynamic property (e.g. capturing / conflict / state)."""
    style = widget.style()  # type: ignore[attr-defined]
    style.unpolish(widget)
    style.polish(widget)
