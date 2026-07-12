from __future__ import annotations

import logging

from sqlmodel import Session

from backend.common.security.policy import InputSanitizer
import backend.common.services.intelligence_feed.repository as repository
from backend.common.services.intelligence_feed.feed_deduper import FeedDeduper
from backend.common.services.intelligence_feed.feed_scorer import FeedScorer
from backend.common.services.intelligence_feed.feed_triage import FeedTriage
from backend.common.services.intelligence_feed.ingestion_events import load_unprocessed_events
from backend.common.services.intelligence_feed.schemas import FeedCard

logger = logging.getLogger(__name__)
_sanitizer = InputSanitizer()


class IntelligenceFeedRouter:
    def __init__(self) -> None:
        self.scorer = FeedScorer()
        self.deduper = FeedDeduper()
        self.triage = FeedTriage()

    def process_new_events(
        self,
        session: Session,
        user_id: int,
        *,
        workspace_ids: tuple[int, ...] = (),
        organization_ids: tuple[int, ...] = (),
        limit: int = 20,
    ) -> int:
        created = 0
        for event in load_unprocessed_events(
            session,
            user_id,
            workspace_ids=workspace_ids,
            organization_ids=organization_ids,
            limit=limit,
        ):
            try:
                score = self.scorer.score(event)
                if score.muted or self.deduper.is_duplicate(session, event, score.topic_key):
                    continue
                triage = self.triage.triage(event, score)
                if not triage.should_create_card:
                    continue
                repository.create_card(
                    session,
                    user_id=user_id,
                    title=triage.title,
                    bullets=triage.bullets,
                    topics=triage.topics,
                    source_type=event.source_type,
                    source_ref=event.source_ref or event.content_hash,
                    topic_key=triage.topic_key,
                    interest_score=triage.interest_score,
                    priority_score=triage.priority_score,
                    raw_event_ids=[event.event_id],
                )
                created += 1
            except Exception as exc:
                logger.exception("Feed event processing failed: %s", _sanitizer.mask_secrets(str(exc)))
        return created

    def list_cards(self, session: Session, user_id: int, *, limit: int = 25) -> list[FeedCard]:
        return repository.list_cards(session, user_id, limit=limit)

    def dismiss(self, session: Session, user_id: int, feed_id: int) -> FeedCard | None:
        return repository.dismiss_card(session, user_id, feed_id)
