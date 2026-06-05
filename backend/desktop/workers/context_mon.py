from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtGui import QClipboard

from backend.common.services.telemetry import TelemetryEvent
from backend.desktop.collectors.clipboard_collector import ClipboardCollector
from backend.desktop.collectors.folder_watch_collector import FolderWatchCollector

logger = logging.getLogger(__name__)


class ContextMonitorWorker:
    """Newsletter-focused wrapper around local context collectors."""

    def __init__(
        self,
        *,
        clipboard: QClipboard,
        session_id: str,
        user_id: int,
        emit: Callable[[TelemetryEvent], None],
    ) -> None:
        self.clipboard_collector = ClipboardCollector(clipboard, session_id, user_id, emit)
        self.folder_watch_collector = FolderWatchCollector(session_id, user_id, emit)

    def start(self, *, clipboard_enabled: bool, folders: list) -> None:
        if clipboard_enabled:
            self.clipboard_collector.start(enabled=True)
        if folders:
            self.folder_watch_collector.start(folders)
        logger.info("Newsletter context monitor started.")

    def stop(self) -> None:
        self.clipboard_collector.stop()
        self.folder_watch_collector.stop()
