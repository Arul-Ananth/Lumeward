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
    if effective_mode == THEME_MODE_LIGHT:
        return """
QMainWindow, QDialog, QScrollArea, QWidget {
    background-color: #f5f5f7;
    color: #1c1c1e;
}
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    margin-top: 18px;
    padding: 14px;
}
QGroupBox::title {
    color: #007aff;
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QLineEdit, QTextEdit, QTextBrowser, QComboBox {
    background-color: #ffffff;
    border: 1px solid #c7c7cc;
    border-radius: 6px;
    color: #1c1c1e;
    selection-background-color: #007aff;
}
QLineEdit:focus, QTextEdit:focus, QTextBrowser:focus, QComboBox:focus {
    border: 1px solid #007aff;
}
QPushButton#primaryButton {
    background-color: #007aff;
    color: #ffffff;
    border: 1px solid #007aff;
    border-radius: 6px;
    font-weight: 700;
}
QPushButton#secondaryButton, QToolButton#secondaryButton {
    background-color: transparent;
    color: #3a3a3c;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    padding: 8px 12px;
}
QTextBrowser#digestOutput {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
}
QTextEdit#executionLog {
    background-color: #f2f2f7;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    color: #3a3a3c;
}
QLabel#panelTitle {
    color: #007aff;
    font-weight: 700;
}
QFrame#insightCard {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
}
QLabel#insightTitle {
    color: #1c1c1e;
    font-weight: 700;
}
QLabel#insightMeta, QLabel#insightBullet, QLabel#insightTopics, QLabel#feedEmpty {
    color: #3a3a3c;
}
"""
    return """
QMainWindow, QDialog, QScrollArea, QWidget {
    background-color: #121212;
    color: #e5e5ea;
}
QGroupBox {
    background-color: #1c1c1e;
    border: 1px solid #2c2c2e;
    border-radius: 8px;
    margin-top: 18px;
    padding: 14px;
}
QGroupBox::title {
    color: #00f2fe;
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QLabel {
    color: #e5e5ea;
}
QLineEdit, QTextEdit, QTextBrowser, QComboBox {
    background-color: #18181a;
    border: 1px solid #2c2c2e;
    border-radius: 6px;
    color: #e5e5ea;
    selection-background-color: #00a7b5;
}
QLineEdit:focus, QTextEdit:focus, QTextBrowser:focus, QComboBox:focus {
    border: 1px solid #00f2fe;
}
QPushButton {
    background-color: #242426;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
    color: #e5e5ea;
    padding: 8px 12px;
}
QPushButton#primaryButton {
    background-color: #00f2fe;
    color: #111112;
    border: 1px solid #00f2fe;
    border-radius: 6px;
    font-weight: 700;
}
QPushButton#secondaryButton, QToolButton#secondaryButton {
    background-color: transparent;
    color: #c7c7cc;
    border: 1px solid #2c2c2e;
    border-radius: 6px;
    padding: 8px 12px;
}
QPushButton:disabled {
    color: #6f6f73;
    border-color: #2c2c2e;
}
QTextBrowser#digestOutput {
    background-color: #161617;
    border: 1px solid #2c2c2e;
    border-radius: 8px;
}
QTextEdit#executionLog {
    background-color: #18181a;
    border: 1px solid #2c2c2e;
    border-radius: 6px;
    color: #c7c7cc;
}
QLabel#panelTitle {
    color: #00f2fe;
    font-weight: 700;
}
QFrame#insightCard {
    background-color: #1c1c1e;
    border: 1px solid #2c2c2e;
    border-radius: 8px;
}
QLabel#insightTitle {
    color: #f5f5f7;
    font-weight: 700;
}
QLabel#insightMeta, QLabel#insightBullet, QLabel#insightTopics, QLabel#feedEmpty {
    color: #c7c7cc;
}
"""


def install_system_theme_listener(app: QApplication) -> None:
    style_hints = app.styleHints()
    signal = getattr(style_hints, "colorSchemeChanged", None)
    if signal is None:
        return

    def _refresh_theme(*_args) -> None:
        if normalize_theme_mode(get_theme_mode()) == THEME_MODE_SYSTEM:
            apply_app_theme(app, THEME_MODE_SYSTEM)

    signal.connect(_refresh_theme)
