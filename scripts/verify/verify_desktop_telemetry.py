import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.append(str(root))

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QTextEdit

from backend.common.config import AppMode, settings
from backend.common.services.telemetry.event_bus import TelemetryEvent
from backend.desktop.collectors import ClipboardCollector, ReaderTelemetryCollector


def main() -> int:
    settings.APP_MODE = AppMode.DESKTOP
    settings.DATA_COLLECTION_ENABLED = True
    settings.CLIPBOARD_COLLECTION_ENABLED = True
    settings.MIN_CLIPBOARD_CHARS = 1
    settings.CLIPBOARD_MAX_CHARS = 50
    settings.configure()

    app = QApplication.instance() or QApplication([])
    events: list[TelemetryEvent] = []

    def emit(event: TelemetryEvent) -> None:
        events.append(event)

    clipboard = app.clipboard()
    clipboard_collector = ClipboardCollector(clipboard, "session", 1, emit)
    clipboard_collector.start()

    output = QTextEdit()
    output.setText("Telemetry output")
    reader = ReaderTelemetryCollector(output, "session", emit)
    reader.start()
    reader.mark_output_start()

    clipboard.setText("https://example.com clipboard text")
    app.processEvents()
    clipboard.setText("x" * 60)
    app.processEvents()

    output.verticalScrollBar().setValue(output.verticalScrollBar().maximum())
    time.sleep(1.1)
    reader._on_scroll(output.verticalScrollBar().value())

    key_event = QKeyEvent(QEvent.KeyPress, Qt.Key_C, Qt.ControlModifier)
    reader.eventFilter(output, key_event)

    reader.flush_output_time()

    event_types = {event.event_type for event in events}
    required = {"clipboard", "telemetry_scroll", "telemetry_copy", "telemetry_output_time"}
    missing = required - event_types
    if missing:
        print(f"FAIL: missing telemetry events: {sorted(missing)}")
        return 1
    oversized = [
        event
        for event in events
        if event.event_type == "clipboard" and event.payload.get("text") == "x" * 60
    ]
    if oversized:
        print("FAIL: oversized clipboard item was emitted.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
