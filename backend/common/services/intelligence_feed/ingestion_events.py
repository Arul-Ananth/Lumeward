from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, select

from backend.common.config import AppMode, settings
from backend.common.models.sql import ContextTag, EventRaw, IntelligenceFeed, Tag
from backend.common.security.policy import InputSanitizer
from backend.common.services.intelligence_feed.schemas import NormalizedEvent

_sanitizer = InputSanitizer()
FEED_EVENT_TYPES = {"clipboard", "file_ingestion", "generate_newsletter", "workspace_context"}


def load_unprocessed_events(
    session: Session,
    user_id: int,
    *,
    workspace_ids: tuple[int, ...] = (),
    organization_ids: tuple[int, ...] = (),
    limit: int = 20,
) -> list[NormalizedEvent]:
    processed_ids = _processed_event_ids(session, user_id)
    statement = select(EventRaw).where(EventRaw.event_type.in_(FEED_EVENT_TYPES))
    # Desktop legacy rows predate ownership columns and are safe only because
    # desktop storage is single-user. Server rows must always be owner-scoped.
    if settings.APP_MODE == AppMode.DESKTOP:
        statement = statement.where(
            (EventRaw.owner_user_id == user_id) | EventRaw.owner_user_id.is_(None)
        )
    else:
        allowed = [EventRaw.owner_user_id == user_id]
        if workspace_ids:
            allowed.append(
                (EventRaw.workspace_id.in_([str(value) for value in workspace_ids]))
                & (EventRaw.visibility == "workspace")
            )
        if organization_ids:
            allowed.append(
                (EventRaw.organization_id.in_([str(value) for value in organization_ids]))
                & (EventRaw.visibility == "organization")
            )
        from sqlalchemy import or_
        statement = statement.where(or_(*allowed))
    events = session.exec(statement.order_by(EventRaw.ts.desc()).limit(limit * 5)).all()
    normalized: list[NormalizedEvent] = []
    event_tags = _event_tags(session, [event.id for event in events if event.id is not None])
    for event in events:
        if event.id is None or event.id in processed_ids:
            continue
        item = normalize_event(
            event,
            user_id,
            workspace_ids=workspace_ids,
            organization_ids=organization_ids,
            tags=event_tags.get(int(event.id or 0), []),
        )
        if item is not None:
            normalized.append(item)
        if len(normalized) >= limit:
            break
    return normalized


def normalize_event(
    event: EventRaw,
    user_id: int,
    *,
    workspace_ids: tuple[int, ...] = (),
    organization_ids: tuple[int, ...] = (),
    tags: list[str] | None = None,
) -> NormalizedEvent | None:
    if event.event_type not in FEED_EVENT_TYPES:
        return None
    if event.visibility == "private" and event.owner_user_id is not None and event.owner_user_id != user_id:
        return None
    if event.visibility == "workspace" and event.workspace_id not in {str(value) for value in workspace_ids}:
        return None
    if event.visibility == "organization" and event.organization_id not in {str(value) for value in organization_ids}:
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
        tags=tags or [],
    )


def _event_tags(session: Session, event_ids: list[int]) -> dict[int, list[str]]:
    if not event_ids:
        return {}
    rows = session.exec(
        select(ContextTag.event_id, Tag.display_name)
        .join(Tag, Tag.id == ContextTag.tag_id)
        .where(ContextTag.event_id.in_(event_ids))
    ).all()
    result: dict[int, list[str]] = {}
    for event_id, display_name in rows:
        result.setdefault(int(event_id), []).append(display_name)
    return result


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
        return f"File added for local indexing: {Path(str(payload['path'])).stem}"
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
