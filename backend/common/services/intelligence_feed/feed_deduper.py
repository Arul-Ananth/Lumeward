from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session

import backend.common.services.intelligence_feed.repository as repository
from backend.common.services.intelligence_feed.schemas import NormalizedEvent


class FeedDeduper:
    def is_duplicate(self, session: Session, event: NormalizedEvent, topic_key: str) -> bool:
        if repository.source_ref_exists(session, event.user_id, event.source_ref):
            return True
        if repository.source_ref_exists(session, event.user_id, event.content_hash):
            return True
        recent_cutoff = datetime.utcnow() - timedelta(hours=6)
        return repository.recent_topic_exists(session, event.user_id, topic_key, recent_cutoff)
