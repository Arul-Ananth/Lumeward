from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtWidgets import QApplication, QTextEdit

from backend.common.config import settings
from backend.common.services.memory.vector_db import client as qdrant_client
from backend.common.services.telemetry import EventPriority, TelemetryEvent
from backend.common.services.telemetry.consent import get_consented_folders
from backend.desktop.collectors import ClipboardCollector, FileDropCollector, FolderWatchCollector, ReaderTelemetryCollector
from backend.desktop.preferences import (
    get_clipboard_collection_enabled,
    get_clipboard_store_raw_text_enabled,
    get_data_collection_enabled,
)
from backend.desktop.services.telemetry_runtime import TelemetryRuntime

logger = logging.getLogger(__name__)


class TelemetryManager:
    def __init__(self, user_id: int, session_id: str, output: QTextEdit, enterprise_dispatch=None) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self.output = output

        self.runtime = TelemetryRuntime()
        self.clipboard_collector = ClipboardCollector(QApplication.clipboard(), session_id, user_id, self.emit)
        self.file_drop_collector = FileDropCollector(session_id, user_id, self.emit)
        self.folder_watch_collector = FolderWatchCollector(session_id, user_id, self.emit)
        self.reader_telemetry = ReaderTelemetryCollector(output, session_id, self.emit)
        self._data_collection_enabled = settings.DATA_COLLECTION_ENABLED
        self._clipboard_collection_enabled = False
        self._enterprise_dispatch = enterprise_dispatch

    def start(self) -> None:
        self._sync_runtime_preferences()
        if not self._data_collection_enabled:
            logger.info('Desktop telemetry collection disabled by user preference.')
            return

        if self._enterprise_dispatch is not None:
            if self._clipboard_collection_enabled:
                self.clipboard_collector.start(enabled=True)
            return

        try:
            self.runtime.start()
        except Exception as exc:
            logger.exception('Failed to start telemetry runtime: %s', exc)
            return

        self.reader_telemetry.start()
        if self._clipboard_collection_enabled:
            self.clipboard_collector.start(enabled=True)

        if settings.FOLDER_WATCH_ENABLED:
            folders = get_consented_folders()
            self.folder_watch_collector.start(folders)

        self.emit_session_start()

    def shutdown(self) -> None:
        self.clipboard_collector.stop()
        self.folder_watch_collector.stop()
        if self._data_collection_enabled and self._enterprise_dispatch is None:
            self.runtime.shutdown()

        try:
            qdrant_client.close()
        except Exception:
            pass

    def emit(self, event: TelemetryEvent) -> None:
        if not self._data_collection_enabled:
            return
        if self._enterprise_dispatch is not None:
            if event.event_type == "clipboard" and settings.CLIPBOARD_STORE_RAW_TEXT:
                text = str(event.payload.get("text") or "")
                if text:
                    self._enterprise_dispatch(text, "clipboard", "Clipboard")
            return
        self.runtime.enqueue(event)

    def emit_session_start(self) -> None:
        payload = {'ts': datetime.utcnow().isoformat(), 'user_id': self.user_id}
        event = TelemetryEvent(
            event_type='session_start',
            session_id=self.session_id,
            payload=payload,
            source='session',
            priority=EventPriority.CRITICAL,
        )
        self.emit(event)

    def emit_session_end(self) -> None:
        payload = {'ts': datetime.utcnow().isoformat(), 'user_id': self.user_id}
        event = TelemetryEvent(
            event_type='session_end',
            session_id=self.session_id,
            payload=payload,
            source='session',
            priority=EventPriority.CRITICAL,
        )
        self.emit(event)

    def emit_generation(self, topic: str, context: str) -> None:
        payload = {
            'topic': topic,
            'context': context,
            'user_id': self.user_id,
            'ts': datetime.utcnow().isoformat(),
        }
        event = TelemetryEvent(
            event_type='generate_newsletter',
            session_id=self.session_id,
            payload=payload,
            source='ui',
            priority=EventPriority.CRITICAL,
        )
        self.emit(event)

    def mark_output_start(self) -> None:
        if not self._data_collection_enabled:
            return
        self.reader_telemetry.mark_output_start()

    def flush_output_time(self) -> None:
        if not self._data_collection_enabled:
            return
        self.reader_telemetry.flush_output_time()

    def handle_file_drop(self, paths: list[str]) -> None:
        if not self._data_collection_enabled:
            return
        self.file_drop_collector.handle_paths(paths)

    def reload_preferences(self) -> None:
        previous_data_enabled = self._data_collection_enabled
        previous_clipboard_enabled = self._clipboard_collection_enabled

        self._sync_runtime_preferences()

        if not previous_data_enabled and self._data_collection_enabled:
            self.start()
            return

        if previous_data_enabled and not self._data_collection_enabled:
            self.clipboard_collector.stop()
            self.folder_watch_collector.stop()
            return

        if self._clipboard_collection_enabled and not previous_clipboard_enabled:
            self.clipboard_collector.start(enabled=True)
            logger.info("Clipboard collection enabled from updated desktop preferences.")
        elif previous_clipboard_enabled and not self._clipboard_collection_enabled:
            self.clipboard_collector.stop()
            logger.info("Clipboard collection disabled from updated desktop preferences.")

    def _sync_runtime_preferences(self) -> None:
        self._data_collection_enabled = get_data_collection_enabled()
        self._clipboard_collection_enabled = self._data_collection_enabled and get_clipboard_collection_enabled()
        settings.DATA_COLLECTION_ENABLED = self._data_collection_enabled
        settings.CLIPBOARD_COLLECTION_ENABLED = self._clipboard_collection_enabled
        settings.CLIPBOARD_STORE_RAW_TEXT = (
            self._clipboard_collection_enabled and get_clipboard_store_raw_text_enabled()
        )
