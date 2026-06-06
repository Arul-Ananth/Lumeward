from __future__ import annotations

import asyncio
import logging

from PySide6.QtCore import QThread, Signal
from sqlmodel import Session

from backend.common.database import engine
from backend.common.security.policy import InputSanitizer
from backend.common.services.intelligence_feed.feed_deep_dive import run_deep_dive

logger = logging.getLogger(__name__)
_sanitizer = InputSanitizer()


class FeedDeepDiveWorker(QThread):
    result_ready = Signal(int, str)
    error_message = Signal(int, str)

    def __init__(
        self,
        user_id: int,
        feed_id: int,
        session_id: str,
        api_keys: dict[str, str | None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.user_id = user_id
        self.feed_id = feed_id
        self.session_id = session_id
        self.api_keys = api_keys or {}

    def run(self) -> None:
        try:
            with Session(engine) as session:
                markdown = asyncio.run(
                    run_deep_dive(
                        session,
                        user_id=self.user_id,
                        feed_id=self.feed_id,
                        session_id=self.session_id,
                        api_keys=self.api_keys,
                    )
                )
            self.result_ready.emit(self.feed_id, markdown)
        except Exception as exc:
            logger.exception("Feed deep dive failed: %s", exc)
            self.error_message.emit(self.feed_id, f"Deep Dive failed: {_sanitizer.mask_secrets(str(exc))}")
