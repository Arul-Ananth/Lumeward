from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime

from sqlmodel import Session

from backend.common.database import get_engine
from backend.common.services.newsletter.pipeline import GenerationRequest, due_schedules, mark_schedule_run, newsletter_pipeline

logger = logging.getLogger(__name__)


class CronDigestWorker:
    """Runs due newsletter schedules in a lightweight background thread."""

    def __init__(self, *, poll_seconds: int = 60) -> None:
        self.poll_seconds = poll_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="LumewardCronDigest", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.poll_seconds)

    def run_once(self, now: datetime | None = None) -> int:
        generated = 0
        with Session(get_engine()) as session:
            schedules = due_schedules(session, now=now)
            for schedule in schedules:
                try:
                    asyncio.run(
                        newsletter_pipeline.generate(
                            GenerationRequest(
                                topic=schedule.topic_seed,
                                user_id=schedule.user_id,
                                source="schedule",
                                template_key=schedule.template_key,
                                source_schedule_id=schedule.id,
                            ),
                            session=session,
                        )
                    )
                    mark_schedule_run(session, schedule)
                    generated += 1
                except Exception as exc:
                    logger.exception("Scheduled newsletter generation failed for schedule %s: %s", schedule.id, exc)
                if self._stop_event.is_set():
                    break
        return generated
