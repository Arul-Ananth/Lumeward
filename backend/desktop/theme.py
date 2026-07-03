from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from backend.desktop.preferences import get_theme_mode

THEME_MODE_SYSTEM = "system"
THEME_MODE_DARK = "dark"
THEME_MODE_LIGHT = "light"

_THEME_FILES = {
    THEME_MODE_DARK: "dark_teal.xml",
    THEME_MODE_LIGHT: "light_cyan.xml",
}

_THEME_QSS_TOKENS = {
    THEME_MODE_LIGHT: {
        "window_bg": "#f5f5f7",
        "text": "#1c1c1e",
        "group_bg": "#ffffff",
        "border": "#d1d1d6",
        "accent": "#007aff",
        "input_bg": "#ffffff",
        "input_border": "#c7c7cc",
        "input_selection": "#007aff",
        "primary_text": "#ffffff",
        "secondary_text": "#3a3a3c",
        "digest_bg": "#ffffff",
        "log_bg": "#f2f2f7",
        "card_bg": "#ffffff",
        "insight_title": "#1c1c1e",
        "label_block": "",
        "button_block": "",
        "disabled_block": "",
    },
    THEME_MODE_DARK: {
        "window_bg": "#121212",
        "text": "#e5e5ea",
        "group_bg": "#1c1c1e",
        "border": "#2c2c2e",
        "accent": "#00f2fe",
        "input_bg": "#18181a",
        "input_border": "#2c2c2e",
        "input_selection": "#00a7b5",
        "primary_text": "#111112",
        "secondary_text": "#c7c7cc",
        "digest_bg": "#161617",
        "log_bg": "#18181a",
        "card_bg": "#1c1c1e",
        "insight_title": "#f5f5f7",
        "label_block": "QLabel {\n    color: #e5e5ea;\n}\n",
        "button_block": """QPushButton {
    background-color: #242426;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
    color: #e5e5ea;
    padding: 8px 12px;
}
""",
        "disabled_block": """QPushButton:disabled {
    color: #6f6f73;
    border-color: #2c2c2e;
}
""",
    },
}

_LUMEWARD_QSS_TEMPLATE = """
QMainWindow, QDialog, QScrollArea, QWidget {{
    background-color: {window_bg};
    color: {text};
}}
QGroupBox {{
    background-color: {group_bg};
    border: 1px solid {border};
    border-radius: 8px;
    margin-top: 18px;
    padding: 14px;
}}
QGroupBox::title {{
    color: {accent};
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}
{label_block}QLineEdit, QTextEdit, QTextBrowser, QComboBox {{
    background-color: {input_bg};
    border: 1px solid {input_border};
    border-radius: 6px;
    color: {text};
    selection-background-color: {input_selection};
}}
QLineEdit:focus, QTextEdit:focus, QTextBrowser:focus, QComboBox:focus {{
    border: 1px solid {accent};
}}
{button_block}QPushButton#primaryButton {{
    background-color: {accent};
    color: {primary_text};
    border: 1px solid {accent};
    border-radius: 6px;
    font-weight: 700;
}}
QPushButton#secondaryButton, QToolButton#secondaryButton {{
    background-color: transparent;
    color: {secondary_text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 8px 12px;
}}
{disabled_block}QTextBrowser#digestOutput {{
    background-color: {digest_bg};
    border: 1px solid {border};
    border-radius: 8px;
}}
QTextEdit#executionLog {{
    background-color: {log_bg};
    border: 1px solid {border};
    border-radius: 6px;
    color: {secondary_text};
}}
QLabel#panelTitle {{
    color: {accent};
    font-weight: 700;
}}
QFrame#insightCard {{
    background-color: {card_bg};
    border: 1px solid {border};
    border-radius: 8px;
}}
QLabel#insightTitle {{
    color: {insight_title};
    font-weight: 700;
}}
QLabel#insightMeta, QLabel#insightBullet, QLabel#insightTopics, QLabel#feedEmpty {{
    color: {secondary_text};
}}
"""


def normalize_theme_mode(mode: str | None) -> str:
    if not mode:
        return THEME_MODE_SYSTEM
    lowered = mode.strip().lower()
    if lowered in {THEME_MODE_SYSTEM, THEME_MODE_DARK, THEME_MODE_LIGHT}:
        return lowered
    return THEME_MODE_SYSTEM


def detect_system_theme_mode(app: QApplication | None = None) -> str:
    qt_app = app or QApplication.instance()
    if qt_app is None:
        return THEME_MODE_DARK
    try:
        scheme = qt_app.styleHints().colorScheme()
    except Exception:
        return THEME_MODE_DARK
    return THEME_MODE_DARK if scheme == Qt.ColorScheme.Dark else THEME_MODE_LIGHT


def resolve_effective_theme_mode(mode: str | None, app: QApplication | None = None) -> str:
    normalized = normalize_theme_mode(mode)
    if normalized == THEME_MODE_SYSTEM:
        return detect_system_theme_mode(app)
    return normalized


def apply_app_theme(app: QApplication, mode: str | None = None) -> str:
    preference = normalize_theme_mode(mode or get_theme_mode())
    effective = resolve_effective_theme_mode(preference, app)
    apply_stylesheet(app, theme=_THEME_FILES[effective])
    app.setStyleSheet(app.styleSheet() + "\n" + _lumeward_qss(effective))
    app.setProperty("lumeward.theme_preference", preference)
    app.setProperty("lumeward.theme_effective", effective)
    return effective


def _lumeward_qss(effective_mode: str) -> str:
    return _LUMEWARD_QSS_TEMPLATE.format(**_THEME_QSS_TOKENS[effective_mode]).strip()


def install_system_theme_listener(app: QApplication) -> None:
    style_hints = app.styleHints()
    signal = getattr(style_hints, "colorSchemeChanged", None)
    if signal is None:
        return

    def _refresh_theme(*_args) -> None:
        if normalize_theme_mode(get_theme_mode()) == THEME_MODE_SYSTEM:
            apply_app_theme(app, THEME_MODE_SYSTEM)

    signal.connect(_refresh_theme)
