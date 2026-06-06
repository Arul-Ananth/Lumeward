from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from backend.common.services.intelligence_feed.schemas import FeedCard


class InsightCard(QFrame):
    dismiss_requested = Signal(int)
    deep_dive_requested = Signal(int)

    def __init__(self, card: FeedCard, parent=None) -> None:
        super().__init__(parent)
        self.card = card
        self.setObjectName("insightCard")
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(7)

        header = QHBoxLayout()
        title = QLabel(card.title)
        title.setObjectName("insightTitle")
        title.setWordWrap(True)
        header.addWidget(title, 1)

        self.dismiss_button = QPushButton("Dismiss")
        self.deep_dive_button = QPushButton("Deep Dive")
        self.dismiss_button.setMinimumHeight(32)
        self.deep_dive_button.setMinimumHeight(32)
        self.dismiss_button.clicked.connect(self._request_dismiss)
        self.deep_dive_button.clicked.connect(self._request_deep_dive)
        header.addWidget(self.dismiss_button)
        header.addWidget(self.deep_dive_button)
        layout.addLayout(header)

        meta = QLabel(f"{_relative_time(card.created_at)} | {card.source_type}")
        meta.setObjectName("insightMeta")
        layout.addWidget(meta)

        for bullet in card.bullets[:3]:
            label = QLabel(f"- {bullet}")
            label.setObjectName("insightBullet")
            label.setWordWrap(True)
            layout.addWidget(label)

        if card.topics:
            topics = QLabel(", ".join(card.topics[:4]))
            topics.setObjectName("insightTopics")
            topics.setWordWrap(True)
            layout.addWidget(topics)

    def set_loading(self, loading: bool) -> None:
        self.deep_dive_button.setEnabled(not loading)
        self.dismiss_button.setEnabled(not loading)
        self.deep_dive_button.setText("Loading" if loading else "Deep Dive")

    def _request_dismiss(self) -> None:
        self.dismiss_requested.emit(self.card.id)

    def _request_deep_dive(self) -> None:
        self.deep_dive_requested.emit(self.card.id)


def _relative_time(value: datetime) -> str:
    seconds = max(0, int((datetime.utcnow() - value).total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    return value.strftime("%Y-%m-%d")
