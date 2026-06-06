from __future__ import annotations

from datetime import datetime

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from _bootstrap import setup_project_path

setup_project_path()

from backend.common.models.sql import EventRaw, User  # noqa: E402
from backend.common.services.intelligence_feed.feed_deduper import FeedDeduper  # noqa: E402
from backend.common.services.intelligence_feed.feed_scorer import FeedScorer  # noqa: E402
from backend.common.services.intelligence_feed.feed_triage import FeedTriage, parse_triage_json  # noqa: E402
from backend.common.services.intelligence_feed.ingestion_events import normalize_event  # noqa: E402
from backend.common.services.intelligence_feed.repository import create_card, dismiss_card, list_cards  # noqa: E402


def main() -> int:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(email="feed@example.test", full_name="Feed User", hashed_password="x")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = int(user.id or 0)

        event = EventRaw(
            event_type="clipboard",
            session_id="s1",
            payload_json='{"text": "Ollama local AI model note for PySide desktop architecture."}',
            hash="hash-1",
            source="clipboard",
        )
        session.add(event)
        session.commit()
        session.refresh(event)

        normalized = normalize_event(event, user_id)
        assert normalized is not None

        score = FeedScorer().score(normalized)
        assert score.priority_score > 0
        assert "Local AI" in score.topics

        triage = FeedTriage().triage(normalized, score)
        assert triage.should_create_card
        assert triage.bullets

        row = create_card(
            session,
            user_id=user_id,
            title=triage.title,
            bullets=triage.bullets,
            topics=triage.topics,
            source_type=normalized.source_type,
            source_ref=normalized.source_ref,
            topic_key=triage.topic_key,
            interest_score=triage.interest_score,
            priority_score=triage.priority_score,
            raw_event_ids=[normalized.event_id],
        )
        assert row.id is not None
        assert list_cards(session, user_id)
        assert FeedDeduper().is_duplicate(session, normalized, triage.topic_key)

        dismissed = dismiss_card(session, user_id, int(row.id))
        assert dismissed is not None
        assert dismissed.status == "dismissed"
        assert list_cards(session, user_id) == []

        parsed = parse_triage_json(
            '{"should_create_card": true, "title": "T", "bullets": ["A"], "topics": ["AI"], '
            '"topic_key": "ai", "priority_score": 0.7, "interest_score": 0.8}'
        )
        assert parsed is not None
        assert parse_triage_json("not json") is None

    print("Intelligence feed verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
