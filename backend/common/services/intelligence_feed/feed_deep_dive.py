from __future__ import annotations

import json

from sqlmodel import Session

from backend.common.models.sql import EventRaw
from backend.common.security.policy import InputSanitizer
import backend.common.services.intelligence_feed.repository as repository
from backend.common.services.newsletter.pipeline import newsletter_pipeline

_sanitizer = InputSanitizer()


async def run_deep_dive(session: Session, *, user_id: int, feed_id: int, session_id: str | None = None) -> str:
    row = repository.get_feed_row(session, user_id, feed_id)
    if row is None:
        raise ValueError("Feed card not found.")

    context = _card_context(session, row.raw_event_ids_json)
    result = await newsletter_pipeline.generate_newsletter(
        topic=row.title,
        user_id=user_id,
        session=session,
        context=context,
        session_id=session_id,
    )
    digest_id = _latest_digest_id(session, user_id)
    if digest_id is not None:
        repository.mark_deep_dive_ready(session, user_id, feed_id, digest_id)
    return result.content


def _card_context(session: Session, raw_event_ids_json: str) -> str:
    event_ids = _loads(raw_event_ids_json)
    lines: list[str] = []
    for event_id in event_ids:
        event = session.get(EventRaw, event_id)
        if event is None:
            continue
        payload = _loads_dict(event.payload_json)
        text = payload.get("text") or payload.get("topic") or payload.get("url") or payload.get("path") or ""
        if text:
            lines.append(str(text))
    return _sanitizer.sanitize_context("\n\n".join(lines))


def _latest_digest_id(session: Session, user_id: int) -> int | None:
    from sqlmodel import select
    from backend.common.models.sql import NewsletterDigest

    digest = session.exec(
        select(NewsletterDigest)
        .where(NewsletterDigest.user_id == user_id)
        .order_by(NewsletterDigest.created_at.desc())
    ).first()
    return digest.id if digest is not None else None


def _loads(raw: str) -> list[int]:
    try:
        value = json.loads(raw)
    except Exception:
        return []
    if not isinstance(value, list):
        return []
    return [int(item) for item in value if isinstance(item, int)]


def _loads_dict(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}
