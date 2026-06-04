from __future__ import annotations

import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QClipboard

from backend.common.config import settings
from backend.common.services.telemetry.event_bus import EventPriority, TelemetryEvent

logger = logging.getLogger(__name__)

URL_REGEX = re.compile(r"(https?://\S+)")


class ClipboardCollector(QObject):
    def __init__(
        self,
        clipboard: QClipboard,
        session_id: str,
        user_id: int,
        emit: Callable[[TelemetryEvent], None],
    ) -> None:
        super().__init__()
        self.clipboard = clipboard
        self.session_id = session_id
        self.user_id = user_id
        self.emit = emit
        self._last_hash = ""
        self._last_ts = 0.0
        self._connected = False

    def start(self, enabled: bool | None = None) -> None:
        allowed = settings.CLIPBOARD_COLLECTION_ENABLED if enabled is None else enabled
        if not allowed:
            logger.info("Clipboard collection disabled.")
            return
        if self._connected:
            return
        self.clipboard.dataChanged.connect(self._on_clipboard_change)
        self._connected = True

    def stop(self) -> None:
        if not self._connected:
            return
        try:
            self.clipboard.dataChanged.disconnect(self._on_clipboard_change)
        except Exception:
            pass
        self._connected = False

    def _on_clipboard_change(self) -> None:
        now = time.time()
        if now - self._last_ts < 0.8:
            return
        text = self.clipboard.text().strip()
        if len(text) < settings.MIN_CLIPBOARD_CHARS:
            return
        if len(text) > settings.CLIPBOARD_MAX_CHARS:
            logger.info("Ignoring clipboard item over %s characters.", settings.CLIPBOARD_MAX_CHARS)
            return

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if content_hash == self._last_hash:
            return

        url_match = URL_REGEX.search(text)
        payload = {
            "user_id": self.user_id,
            "url": url_match.group(1) if url_match else "",
            "content_hash": content_hash,
            "ts": datetime.utcnow().isoformat(),
        }
        if settings.CLIPBOARD_STORE_RAW_TEXT:
            payload["text"] = text
        event = TelemetryEvent(
            event_type="clipboard",
            session_id=self.session_id,
            payload=payload,
            source="clipboard",
            priority=EventPriority.IMPORTANT,
            content_hash=content_hash,
        )
        self.emit(event)
        self._last_hash = content_hash
        self._last_ts = now
