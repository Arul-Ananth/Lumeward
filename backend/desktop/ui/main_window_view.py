from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from backend.desktop.ui.collapsible_log_widget import CollapsibleLogWidget
from backend.desktop.widgets.intelligence_feed_panel import IntelligenceFeedPanel

PRESET_GUIDANCE: dict[str, str] = {
    "Beginner": "Write for beginners.",
    "5 bullets": "Format the answer as 5 concise bullets.",
    "Executive": "Use an executive-brief tone.",
    "Today": "Focus only on items from today and cite the date explicitly.",
    "No sports": "Exclude sports coverage.",
}


@dataclass
class MainWindowWidgets:
    central_widget: QScrollArea
    content_widget: QWidget
    topic_input: QLineEdit
    guidance_input: QTextEdit
    attached_context_area: QTextEdit
    status_label: QLabel
    capability_label: QLabel
    generate_btn: QPushButton
    regenerate_btn: QPushButton
    copy_btn: QPushButton
    clear_btn: QPushButton
    save_btn: QPushButton
    result_meta_label: QLabel
    output_area: QTextBrowser
    log_widget: CollapsibleLogWidget
    feed_panel: IntelligenceFeedPanel
    preset_buttons: dict[str, QPushButton]
    workspace_selector: QComboBox


def _build_section(title: str) -> tuple[QGroupBox, QVBoxLayout]:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.setSpacing(10)
    return box, layout


def _build_dropdown(title: str) -> tuple[QToolButton, QWidget, QVBoxLayout]:
    toggle = QToolButton()
    toggle.setText(title)
    toggle.setCheckable(True)
    toggle.setChecked(False)
    toggle.setArrowType(Qt.RightArrow)
    toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    toggle.setObjectName("secondaryButton")

    content = QWidget()
    content.setVisible(False)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    def sync(opened: bool) -> None:
        toggle.setArrowType(Qt.DownArrow if opened else Qt.RightArrow)
        content.setVisible(opened)

    toggle.toggled.connect(sync)
    return toggle, content, layout


def build_main_window_content() -> MainWindowWidgets:
    content_widget = QWidget()
    root_layout = QVBoxLayout(content_widget)
    root_layout.setSpacing(12)
    root_layout.setContentsMargins(14, 14, 14, 14)

    ask_box, ask_layout = _build_section("Lumeward")
    workspace_selector = QComboBox()
    workspace_selector.setMinimumWidth(220)
    workspace_selector.addItem("Personal workspace", None)
    ask_layout.addWidget(workspace_selector)
    topic_input = QLineEdit()
    topic_input.setPlaceholderText("Search / Ask Lumeward...")
    generate_btn = QPushButton("Generate Brief")
    generate_btn.setObjectName("primaryButton")
    generate_btn.setMinimumHeight(40)
    ask_row = QHBoxLayout()
    ask_row.addWidget(topic_input, 1)
    ask_row.addWidget(generate_btn)
    ask_layout.addLayout(ask_row)
    root_layout.addWidget(ask_box)

    guidance_toggle, guidance_content, guidance_content_layout = _build_dropdown("Guidance")
    root_layout.addWidget(guidance_toggle)

    guide_box, guide_layout = _build_section("Guidance")
    guidance_input = QTextEdit()
    guidance_input.setPlaceholderText("Audience, scope, tone, format")
    guidance_input.setMaximumHeight(110)
    guide_layout.addWidget(guidance_input)

    presets_layout = QGridLayout()
    preset_buttons: dict[str, QPushButton] = {}
    for index, label in enumerate(PRESET_GUIDANCE):
        button = QPushButton(label)
        button.setMinimumHeight(32)
        presets_layout.addWidget(button, index // 3, index % 3)
        preset_buttons[label] = button
    guide_layout.addLayout(presets_layout)

    attached_context_area = QTextEdit()
    attached_context_area.setReadOnly(True)
    attached_context_area.setPlaceholderText("Attached context")
    attached_context_area.setMaximumHeight(110)
    guide_layout.addWidget(attached_context_area)
    guidance_content_layout.addWidget(guide_box)
    root_layout.addWidget(guidance_content)

    status_label = QLabel("Idle")
    status_label.hide()
    status_label.setWordWrap(True)
    capability_label = QLabel("Search unavailable")
    capability_label.hide()
    capability_label.setWordWrap(True)

    result_box, result_layout = _build_section("Deep Dive Viewer")
    result_meta_label = QLabel("No result")
    result_meta_label.hide()
    result_meta_label.setWordWrap(True)
    result_meta_label.setStyleSheet("padding: 6px; border-radius: 6px;")

    result_actions = QHBoxLayout()
    regenerate_btn = QPushButton("Regenerate")
    copy_btn = QPushButton("Copy")
    clear_btn = QPushButton("Clear")
    save_btn = QPushButton("Save")
    for button in (regenerate_btn, copy_btn, clear_btn, save_btn):
        result_actions.addWidget(button)
    result_actions.addStretch(1)
    result_layout.addLayout(result_actions)

    output_area = QTextBrowser()
    output_area.setObjectName("digestOutput")
    output_area.setReadOnly(True)
    output_area.setOpenExternalLinks(False)
    output_area.setMinimumHeight(320)
    output_area.setPlaceholderText("Generated brief")
    result_layout.addWidget(output_area, 1)

    log_widget = CollapsibleLogWidget()
    result_layout.addWidget(log_widget)

    feed_panel = IntelligenceFeedPanel()
    main_splitter = QSplitter(Qt.Horizontal)
    main_splitter.addWidget(feed_panel)
    main_splitter.addWidget(result_box)
    main_splitter.setStretchFactor(0, 1)
    main_splitter.setStretchFactor(1, 2)
    root_layout.addWidget(main_splitter, 1)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(content_widget)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    return MainWindowWidgets(
        central_widget=scroll_area,
        content_widget=content_widget,
        topic_input=topic_input,
        guidance_input=guidance_input,
        attached_context_area=attached_context_area,
        status_label=status_label,
        capability_label=capability_label,
        generate_btn=generate_btn,
        regenerate_btn=regenerate_btn,
        copy_btn=copy_btn,
        clear_btn=clear_btn,
        save_btn=save_btn,
        result_meta_label=result_meta_label,
        output_area=output_area,
        log_widget=log_widget,
        feed_panel=feed_panel,
        preset_buttons=preset_buttons,
        workspace_selector=workspace_selector,
    )
