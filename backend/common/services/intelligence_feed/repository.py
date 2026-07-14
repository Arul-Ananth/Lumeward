from __future__ import annotations

import json
from datetime import datetime

from sqlmodel import Session, select

from backend.common.models.sql import IntelligenceFeed
from backend.common.services.intelligence_feed.schemas import FeedCard

ACTIVE_STATUSES = ("new", "seen", "deep_dive_ready")
VISIBLE_SOURCE_TYPES = ("clipboard", "file_drop", "folder_watch", "folder_upload", "ui", "web")


def list_cards(session: Session, user_id: int, *, limit: int = 25) -> list[FeedCard]:
    statement = (
        select(IntelligenceFeed)
        .where(
            IntelligenceFeed.user_id == user_id,
            IntelligenceFeed.status.in_(ACTIVE_STATUSES),
            IntelligenceFeed.source_type.in_(VISIBLE_SOURCE_TYPES),
        )
        .order_by(IntelligenceFeed.priority_score.desc(), IntelligenceFeed.created_at.desc())
        .limit(limit)
    )
    return [_to_card(row) for row in session.exec(statement).all()]


def get_feed_row(session: Session, user_id: int, feed_id: int) -> IntelligenceFeed | None:
    row = session.get(IntelligenceFeed, feed_id)
    if row is None or row.user_id != user_id:
        return None
    return row


def source_ref_exists(session: Session, user_id: int, source_ref: str) -> bool:
    statement = select(IntelligenceFeed).where(
        IntelligenceFeed.user_id == user_id,
        IntelligenceFeed.source_ref == source_ref,
    )
    return session.exec(statement).first() is not None


def recent_topic_exists(session: Session, user_id: int, topic_key: str, since: datetime) -> bool:
    statement = select(IntelligenceFeed).where(
        IntelligenceFeed.user_id == user_id,
        IntelligenceFeed.topic_key == topic_key,
        IntelligenceFeed.created_at >= since,
        IntelligenceFeed.status != "dismissed",
    )
    return session.exec(statement).first() is not None


def create_card(
    session: Session,
    *,
    user_id: int,
    title: str,
    bullets: list[str],
    topics: list[str],
    source_type: str,
    source_ref: str,
    topic_key: str,
    interest_score: float,
    priority_score: float,
    raw_event_ids: list[int],
) -> IntelligenceFeed:
    row = IntelligenceFeed(
        user_id=user_id,
        title=title[:200],
        summary_json=json.dumps({"bullets": bullets[:3]}, ensure_ascii=True),
        source_type=source_type[:80],
        source_ref=source_ref[:512],
        topic_key=topic_key[:120],
        topics_json=json.dumps(topics[:8], ensure_ascii=True),
        interest_score=interest_score,
        priority_score=priority_score,
        status="new",
        raw_event_ids_json=json.dumps(raw_event_ids, ensure_ascii=True),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def dismiss_card(session: Session, user_id: int, feed_id: int) -> FeedCard | None:
    row = get_feed_row(session, user_id, feed_id)
    if row is None:
        return None
    row.status = "dismissed"
    row.dismissed_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_card(row)


def mark_deep_dive_ready(session: Session, user_id: int, feed_id: int, digest_id: int) -> FeedCard | None:
    row = get_feed_row(session, user_id, feed_id)
    if row is None:
        return None
    row.status = "deep_dive_ready"
    row.deep_dive_digest_id = digest_id
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_card(row)


def mark_failed(session: Session, user_id: int, feed_id: int, reason: str) -> None:
    row = get_feed_row(session, user_id, feed_id)
    if row is None:
        return
    row.status = "failed"
    row.failure_reason = reason[:1000]
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()


def _to_card(row: IntelligenceFeed) -> FeedCard:
    summary = _loads(row.summary_json, {})
    topics = _loads(row.topics_json, [])
    bullets = summary.get("bullets", []) if isinstance(summary, dict) else []
    return FeedCard(
        id=int(row.id or 0),
        title=row.title,
        bullets=[str(item) for item in bullets][:3],
        topics=[str(item) for item in topics][:8],
        source_type=row.source_type,
        priority_score=row.priority_score,
        interest_score=row.interest_score,
        created_at=row.created_at,
        status=row.status,
    )


def _loads(raw: str, fallback):
    try:
        return json.loads(raw)
    except Exception:
        return fallback
