from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from backend.common.services.intelligence_feed.schemas import FeedCard
from backend.desktop.widgets.insight_card import InsightCard


class IntelligenceFeedPanel(QWidget):
    dismiss_requested = Signal(int)
    deep_dive_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: dict[int, InsightCard] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Personal Feed")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.empty_label = QLabel("No feed cards yet")
        self.empty_label.setObjectName("feedEmpty")
        self.empty_label.setWordWrap(True)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("feedScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(10)
        self.content_layout.addWidget(self.empty_label)
        self.content_layout.addStretch(1)
        self.scroll_area.setWidget(self.content)
        layout.addWidget(self.scroll_area, 1)

    def set_cards(self, cards: list[FeedCard]) -> None:
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

        if not cards:
            self.empty_label = QLabel("No feed cards yet")
            self.empty_label.setObjectName("feedEmpty")
            self.content_layout.addWidget(self.empty_label)
            self.content_layout.addStretch(1)
            return

        for card in cards:
            widget = InsightCard(card)
            widget.dismiss_requested.connect(self.dismiss_requested)
            widget.deep_dive_requested.connect(self.deep_dive_requested)
            self._cards[card.id] = widget
            self.content_layout.addWidget(widget)
        self.content_layout.addStretch(1)

    def set_card_loading(self, feed_id: int, loading: bool) -> None:
        card = self._cards.get(feed_id)
        if card is not None:
            card.set_loading(loading)
