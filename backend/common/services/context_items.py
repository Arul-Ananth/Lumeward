from __future__ import annotations

from sqlmodel import Session

from backend.common.models.sql import ContextItem, EventRaw


def create_context_item(session: Session, event: EventRaw) -> ContextItem:
    """Create the canonical lifecycle record for an ingested raw event."""
    item = ContextItem(
        event_id=event.id,
        organization_id=event.organization_id,
        workspace_id=event.workspace_id,
        owner_user_id=event.owner_user_id,
        visibility=event.visibility,
        source=event.source,
        external_id=event.hash,
        content_type="text",
        classification="internal",
        processing_purpose="context_retrieval",
        created_at=event.ts,
    )
    session.add(item)
    return item
