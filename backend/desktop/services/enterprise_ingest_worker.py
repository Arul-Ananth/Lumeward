from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from backend.common.services.telemetry.ingestion import extract_text_from_file
from backend.desktop.services.enterprise_client import EnterpriseClient


class EnterpriseIngestWorker(QThread):
    completed = Signal(str)
    error_message = Signal(str)

    def __init__(
        self,
        client: EnterpriseClient,
        *,
        text: str = "",
        source: str,
        title: str = "",
        path: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.text = text
        self.source = source
        self.title = title
        self.path = path

    def run(self) -> None:
        try:
            content = self.text
            title = self.title
            if self.path:
                file_path = Path(self.path)
                content, error = extract_text_from_file(file_path)
                if error:
                    raise ValueError(error)
                title = title or file_path.name
            chunks = self.client.ingest_context(content or "", self.source, title)
            self.completed.emit(f"Shared {chunks} context chunk(s) with the selected workspace.")
        except Exception as exc:
            self.error_message.emit(f"Enterprise context was not shared: {exc}")
