from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal
from sqlmodel import Session

from backend.common.database import get_engine
from backend.common.services.intelligence_feed.feed_router import IntelligenceFeedRouter

logger = logging.getLogger(__name__)


class FeedProcessorWorker(QThread):
    processed = Signal(int)
    error_message = Signal(str)

    def __init__(self, user_id: int, parent=None) -> None:
        super().__init__(parent)
        self.user_id = user_id

    def run(self) -> None:
        try:
            with Session(get_engine()) as session:
                created = IntelligenceFeedRouter().process_new_events(session, self.user_id)
            self.processed.emit(created)
        except Exception as exc:
            logger.exception("Feed processing failed: %s", exc)
            self.error_message.emit("Feed processing failed.")
