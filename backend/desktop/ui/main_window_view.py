from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend.desktop.ui.collapsible_log_widget import CollapsibleLogWidget

PRESET_GUIDANCE: dict[str, str] = {
    "For beginners": "Write for beginners.",
    "5 bullets": "Format the answer as 5 concise bullets.",
    "Executive tone": "Use an executive-brief tone.",
    "Only today": "Focus only on items from today and cite the date explicitly.",
    "Avoid sports": "Exclude sports coverage.",
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
    preset_buttons: dict[str, QPushButton]


def _build_section(title: str) -> tuple[QGroupBox, QVBoxLayout]:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.setSpacing(10)
    return box, layout


def build_main_window_content() -> MainWindowWidgets:
    content_widget = QWidget()
    root_layout = QVBoxLayout(content_widget)
    root_layout.setSpacing(12)
    root_layout.setContentsMargins(14, 14, 14, 14)

    ask_box, ask_layout = _build_section("Ask")
    ask_layout.addWidget(QLabel("Topic / Query"))
    topic_input = QLineEdit()
    topic_input.setPlaceholderText("Example: current world events, AI regulation, or what did I just copy")
    ask_layout.addWidget(topic_input)
    root_layout.addWidget(ask_box)

    guide_box, guide_layout = _build_section("Guide")
    guide_layout.addWidget(QLabel("Optional Guidance: add audience, scope, tone, format, or exclusions."))
    guidance_input = QTextEdit()
    guidance_input.setPlaceholderText("Example: for beginners, 5 bullets, focus on Europe, neutral tone.")
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

    guide_layout.addWidget(QLabel("Attached Context"))
    attached_context_area = QTextEdit()
    attached_context_area.setReadOnly(True)
    attached_context_area.setPlaceholderText("Bridge URLs, OCR text, and other attached context will appear here.")
    attached_context_area.setMaximumHeight(110)
    guide_layout.addWidget(attached_context_area)
    root_layout.addWidget(guide_box)

    run_box, run_layout = _build_section("Run")
    status_label = QLabel("Status: Idle")
    status_label.setWordWrap(True)
    capability_label = QLabel("Search: Unknown")
    capability_label.setWordWrap(True)
    run_layout.addWidget(status_label)
    run_layout.addWidget(capability_label)

    generate_btn = QPushButton("Generate Brief")
    generate_btn.setObjectName("primaryButton")
    generate_btn.setMinimumHeight(40)
    run_layout.addWidget(generate_btn)
    root_layout.addWidget(run_box)

    result_box, result_layout = _build_section("Result")
    result_meta_label = QLabel("No result generated yet.")
    result_meta_label.setWordWrap(True)
    result_meta_label.setStyleSheet("padding: 6px; border-radius: 6px;")
    result_layout.addWidget(result_meta_label)

    result_actions = QHBoxLayout()
    regenerate_btn = QPushButton("Regenerate")
    copy_btn = QPushButton("Copy")
    clear_btn = QPushButton("Clear")
    save_btn = QPushButton("Save as Markdown")
    for button in (regenerate_btn, copy_btn, clear_btn, save_btn):
        result_actions.addWidget(button)
    result_actions.addStretch(1)
    result_layout.addLayout(result_actions)

    output_area = QTextBrowser()
    output_area.setObjectName("digestOutput")
    output_area.setReadOnly(True)
    output_area.setOpenExternalLinks(False)
    output_area.setMinimumHeight(320)
    output_area.setPlaceholderText("Your generated brief will appear here.")
    result_layout.addWidget(output_area, 1)

    log_widget = CollapsibleLogWidget()
    result_layout.addWidget(log_widget)
    root_layout.addWidget(result_box, 1)

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
        preset_buttons=preset_buttons,
    )
