from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, select

from backend.common.models.sql import EventRaw, IntelligenceFeed
from backend.common.security.policy import InputSanitizer
from backend.common.services.intelligence_feed.schemas import NormalizedEvent

_sanitizer = InputSanitizer()
FEED_EVENT_TYPES = {"clipboard", "file_ingestion", "generate_newsletter"}


def load_unprocessed_events(session: Session, user_id: int, *, limit: int = 20) -> list[NormalizedEvent]:
    processed_ids = _processed_event_ids(session, user_id)
    events = session.exec(
        select(EventRaw).where(EventRaw.event_type.in_(FEED_EVENT_TYPES)).order_by(EventRaw.ts.desc()).limit(limit * 5)
    ).all()
    normalized: list[NormalizedEvent] = []
    for event in events:
        if event.id is None or event.id in processed_ids:
            continue
        item = normalize_event(event, user_id)
        if item is not None:
            normalized.append(item)
        if len(normalized) >= limit:
            break
    return normalized


def normalize_event(event: EventRaw, user_id: int) -> NormalizedEvent | None:
    if event.event_type not in FEED_EVENT_TYPES:
        return None
    payload = _loads(event.payload_json)
    text = _event_text(event, payload)
    if len(text.strip()) < 20:
        return None
    safe_text = _sanitizer.sanitize_context(text)[:2400]
    if not safe_text:
        return None
    source_ref = _source_ref(event, payload)
    return NormalizedEvent(
        event_id=int(event.id or 0),
        user_id=user_id,
        source_type=event.source or event.event_type,
        source_ref=source_ref,
        text=safe_text,
        created_at=event.ts,
        content_hash=event.hash,
    )


def _processed_event_ids(session: Session, user_id: int) -> set[int]:
    rows = session.exec(select(IntelligenceFeed.raw_event_ids_json).where(IntelligenceFeed.user_id == user_id)).all()
    ids: set[int] = set()
    for raw in rows:
        try:
            values = json.loads(raw)
        except Exception:
            continue
        if isinstance(values, list):
            ids.update(int(value) for value in values if isinstance(value, int))
    return ids


def _event_text(event: EventRaw, payload: dict) -> str:
    if event.event_type == "file_ingestion" and payload.get("path"):
        return f"File added: {Path(str(payload['path'])).name}"
    for key in ("text", "topic", "url", "path", "title"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _source_ref(event: EventRaw, payload: dict) -> str:
    for key in ("url", "path", "content_hash"):
        value = payload.get(key)
        if value:
            return str(value)
    return event.hash or f"event:{event.id}"


def _loads(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}
