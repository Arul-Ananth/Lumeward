from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


FEED_STATUSES = {"new", "seen", "dismissed", "deep_dive_ready", "archived", "failed"}


@dataclass(frozen=True)
class FeedCard:
    id: int
    title: str
    bullets: list[str]
    topics: list[str]
    source_type: str
    priority_score: float
    interest_score: float
    created_at: datetime
    status: str


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: int
    user_id: int
    source_type: str
    source_ref: str
    text: str
    created_at: datetime
    content_hash: str
