from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QTextEdit, QVBoxLayout, QWidget


class CollapsibleLogWidget(QWidget):
    def __init__(self, title: str = "Execution Messages", parent=None) -> None:
        super().__init__(parent)
        self._collapsed = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("secondaryButton")
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_button)

        self.log_area = QTextEdit()
        self.log_area.setObjectName("executionLog")
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(120)
        layout.addWidget(self.log_area)

        self._title = title
        self._sync_state()

    def append_message(self, message: str) -> None:
        text = message.strip()
        if text:
            self.log_area.append(text)

    def toggle(self) -> None:
        self._collapsed = not self._collapsed
        self._sync_state()

    def _sync_state(self) -> None:
        indicator = "Show" if self._collapsed else "Hide"
        self.toggle_button.setText(f"{indicator} {self._title}")
        self.log_area.setVisible(not self._collapsed)
