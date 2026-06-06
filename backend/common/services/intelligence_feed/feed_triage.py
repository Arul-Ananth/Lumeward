from __future__ import annotations

import json
import re
from dataclasses import dataclass

from backend.common.services.intelligence_feed.feed_scorer import FeedScore
from backend.common.services.intelligence_feed.schemas import NormalizedEvent


@dataclass(frozen=True)
class TriageResult:
    should_create_card: bool
    title: str
    bullets: list[str]
    topics: list[str]
    topic_key: str
    priority_score: float
    interest_score: float
    needs_web_search: bool = False
    needs_deep_dive: bool = False
    reason: str = ""


class FeedTriage:
    def triage(self, event: NormalizedEvent, score: FeedScore) -> TriageResult:
        title = _title_from_text(event.text, score.topics[0])
        bullets = _bullets_from_text(event.text)
        return TriageResult(
            should_create_card=not score.muted and score.priority_score > 0.0,
            title=title,
            bullets=bullets,
            topics=score.topics,
            topic_key=score.topic_key,
            priority_score=score.priority_score,
            interest_score=score.interest_score,
            needs_web_search=False,
            needs_deep_dive=False,
            reason="Matched local feed scoring rules.",
        )


def parse_triage_json(raw: str) -> TriageResult | None:
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    bullets = payload.get("bullets")
    topics = payload.get("topics")
    if not isinstance(bullets, list) or not isinstance(topics, list):
        return None
    return TriageResult(
        should_create_card=bool(payload.get("should_create_card", False)),
        title=str(payload.get("title") or "Untitled"),
        bullets=[str(item) for item in bullets][:3],
        topics=[str(item) for item in topics][:8],
        topic_key=str(payload.get("topic_key") or "general"),
        priority_score=float(payload.get("priority_score") or 0.0),
        interest_score=float(payload.get("interest_score") or 0.0),
        needs_web_search=bool(payload.get("needs_web_search", False)),
        needs_deep_dive=bool(payload.get("needs_deep_dive", False)),
        reason=str(payload.get("reason") or ""),
    )


def _title_from_text(text: str, fallback_topic: str) -> str:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    cleaned = re.sub(r"\s+", " ", first).strip(" -")
    if not cleaned:
        return fallback_topic
    return cleaned[:72]


def _bullets_from_text(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    bullets = [sentence.strip(" -")[:160] for sentence in sentences if len(sentence.strip()) > 12]
    if not bullets and text.strip():
        bullets = [text.strip()[:160]]
    return bullets[:3] or ["Captured a local event for review."]
