from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    TELEMETRY = 1
    IMPORTANT = 2
    CRITICAL = 3


@dataclass(frozen=True)
class TelemetryEvent:
    event_type: str
    session_id: str
    payload: dict[str, Any]
    source: str
    priority: EventPriority
    ts: datetime = field(default_factory=datetime.utcnow)
    content_hash: str = ""
    organization_id: str | None = None
    workspace_id: str | None = None
    owner_user_id: int | None = None
    visibility: str = "private"


class EventBus:
    def __init__(self, maxsize: int) -> None:
        self.queue: asyncio.Queue[TelemetryEvent] = asyncio.Queue(maxsize=maxsize)

    def enqueue(self, event: TelemetryEvent) -> None:
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            if event.priority == EventPriority.CRITICAL:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.queue.put(event))
                    logger.warning("Event queue full. Scheduling critical event: %s", event.event_type)
                except RuntimeError:
                    logger.error("No running loop to schedule critical event: %s", event.event_type)
            else:
                logger.warning("Event queue full. Dropping %s event: %s", event.priority.name, event.event_type)
