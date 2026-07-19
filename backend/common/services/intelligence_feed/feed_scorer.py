from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from backend.common.services.intelligence_feed.schemas import NormalizedEvent

BOOSTED_KEYWORDS = {
    "ai": ("AI", "Local AI"),
    "llm": ("AI", "Local AI"),
    "ollama": ("AI", "Local AI"),
    "python": ("Python", "Software"),
    "fastapi": ("FastAPI", "Software"),
    "pyside": ("PySide6", "Desktop"),
    "qdrant": ("Qdrant", "Memory"),
    "security": ("Security",),
    "privacy": ("Privacy",),
    "spring": ("Spring Boot", "Software"),
    "jwt": ("Security", "Auth"),
}

MUTED_KEYWORDS = {"advertisement", "sponsored"}


@dataclass(frozen=True)
class FeedScore:
    topic_key: str
    topics: list[str]
    interest_score: float
    priority_score: float
    muted: bool = False


class FeedScorer:
    def score(self, event: NormalizedEvent) -> FeedScore:
        lowered = event.text.lower()
        tokens = set(re.findall(r"[a-z0-9_+-]+", lowered))
        muted = bool(tokens.intersection(MUTED_KEYWORDS))

        topics: list[str] = list(event.tags)
        for keyword, labels in BOOSTED_KEYWORDS.items():
            if keyword in lowered:
                for label in labels:
                    if label not in topics:
                        topics.append(label)

        if not topics:
            topics = [_fallback_topic(event.source_type)]

        topic_key = _topic_key(topics[0])
        interest = min(1.0, 0.35 + (0.12 * len(topics)))
        if event.source_type in {"clipboard", "ui"}:
            interest += 0.1
        priority = min(1.0, interest + _freshness_bonus(event))
        if muted:
            priority = 0.0
            interest = 0.0

        return FeedScore(
            topic_key=topic_key,
            topics=topics,
            interest_score=round(interest, 3),
            priority_score=round(priority, 3),
            muted=muted,
        )


def _fallback_topic(source_type: str) -> str:
    cleaned = source_type.replace("_", " ").strip().title()
    return cleaned or "General"


def _topic_key(label: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return key or "general"


def _freshness_bonus(event: NormalizedEvent) -> float:
    age_seconds = max(0.0, (datetime.utcnow() - event.created_at).total_seconds())
    if age_seconds < 3600:
        return 0.2
    if age_seconds < 86400:
        return 0.1
    return 0.0
