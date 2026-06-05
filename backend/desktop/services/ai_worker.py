from __future__ import annotations

import asyncio
import logging

from PySide6.QtCore import QThread, Signal
from sqlmodel import Session

from backend.common.database import engine
from backend.common.security.policy import InputSanitizer

logger = logging.getLogger(__name__)
_sanitizer = InputSanitizer()


class AIWorker(QThread):
    progress_update = Signal(int)
    status_message = Signal(str)
    result_ready = Signal(str)
    error_message = Signal(str)

    def __init__(
        self,
        topic: str,
        context: str,
        user_id: int,
        session_id: str,
        api_keys: dict[str, str | None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.topic = topic
        self.context = context
        self.user_id = user_id
        self.session_id = session_id
        self.api_keys = api_keys
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        self.requestInterruption()

    def run(self) -> None:
        if self.isInterruptionRequested() or self._cancelled:
            self.status_message.emit("Generation cancelled.")
            self.result_ready.emit("")
            return

        try:
            from backend.common.services.newsletter.pipeline import newsletter_pipeline

            self.status_message.emit("Starting AI generation...")
            with Session(engine) as session:
                result = asyncio.run(
                    newsletter_pipeline.generate_newsletter(
                        topic=self.topic,
                        user_id=self.user_id,
                        session=session,
                        context=self.context,
                        api_keys=self.api_keys,
                        session_id=self.session_id,
                    )
                )
            if self.isInterruptionRequested() or self._cancelled:
                self.status_message.emit("Generation cancelled.")
                self.result_ready.emit("")
                return
            self.result_ready.emit(result.content)
        except Exception as exc:
            logger.exception("AI generation failed: %s", exc)
            message = _format_generation_error(exc)
            self.status_message.emit("Error occurred while generating the newsletter.")
            self.error_message.emit(message)
            self.result_ready.emit("")


def _format_generation_error(exc: Exception) -> str:
    raw = _sanitizer.mask_secrets(str(exc)).strip()
    if isinstance(exc, ModuleNotFoundError):
        missing = getattr(exc, "name", "") or raw
        return f"Generation failed because a packaged dependency is missing: `{missing}`."
    if isinstance(exc, ImportError):
        return f"Generation failed because an LLM provider dependency could not load: {raw}"
    if isinstance(exc, ValueError) and "Unknown encoding" in raw:
        return f"Generation failed because the packaged tokenizer data is incomplete: {raw}"
    if "api key" in raw.lower():
        return f"Generation failed because the configured LLM API key is missing or invalid: {raw}"
    if not raw:
        raw = exc.__class__.__name__
    return f"Generation failed: {raw}"
