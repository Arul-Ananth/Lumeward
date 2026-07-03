from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal
from sqlmodel import Session

from backend.common.database import get_engine
from backend.common.services.intelligence_feed.feed_router import IntelligenceFeedRouter

logger = logging.getLogger(__name__)


class FeedRefreshWorker(QThread):
    cards_ready = Signal(list)
    error_message = Signal(str)

    def __init__(self, user_id: int, parent=None) -> None:
        super().__init__(parent)
        self.user_id = user_id

    def run(self) -> None:
        try:
            with Session(get_engine()) as session:
                cards = IntelligenceFeedRouter().list_cards(session, self.user_id)
            self.cards_ready.emit(cards)
        except Exception as exc:
            logger.exception("Feed refresh failed: %s", exc)
            self.error_message.emit("Feed refresh failed.")


class FeedDismissWorker(QThread):
    completed = Signal(int)
    error_message = Signal(str)

    def __init__(self, user_id: int, feed_id: int, parent=None) -> None:
        super().__init__(parent)
        self.user_id = user_id
        self.feed_id = feed_id

    def run(self) -> None:
        try:
            with Session(get_engine()) as session:
                IntelligenceFeedRouter().dismiss(session, self.user_id, self.feed_id)
            self.completed.emit(self.feed_id)
        except Exception as exc:
            logger.exception("Feed dismiss failed: %s", exc)
            self.error_message.emit("Dismiss failed.")
