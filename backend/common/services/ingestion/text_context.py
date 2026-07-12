"""Workspace-scoped ingestion for explicitly shared desktop text."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from qdrant_client.http import models
from sqlmodel import Session

from backend.common.config import settings
from backend.common.models.sql import EventRaw
from backend.common.services.context_items import create_context_item
from backend.common.services.memory.point_ids import stable_point_id
from backend.common.services.memory.vector_db import client, ensure_collection, get_embedder
from backend.common.services.telemetry.ingestion import chunk_text


def ingest_workspace_text(
    session: Session,
    *,
    text: str,
    source: str,
    user_id: int,
    organization_id: int,
    workspace_id: int,
    title: str = "",
) -> int:
    """Index user-approved text and record its team workspace ownership."""
    content = text.strip()
    if not content:
        raise ValueError("Context text cannot be empty.")
    chunks = chunk_text(content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    if not chunks:
        raise ValueError("Context text cannot be indexed.")
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    ensure_collection(settings.QDRANT_COLLECTION_USER_DOCS)
    vectors = get_embedder().encode(chunks).tolist()
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION_USER_DOCS,
        points=[
            models.PointStruct(
                id=stable_point_id("workspace_text", workspace_id, content_hash, index),
                vector=vector,
                payload={
                    "document": chunks[index],
                    "user_id": str(user_id),
                    "organization_id": str(organization_id),
                    "workspace_id": str(workspace_id),
                    "visibility": "workspace",
                    "source": source,
                    "title": title,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            for index, vector in enumerate(vectors)
        ],
    )
    payload = {"title": title, "content_hash": content_hash, "source": source}
    event = EventRaw(
        event_type="workspace_context",
        session_id="enterprise-desktop",
        payload_json=json.dumps(payload, ensure_ascii=True),
        hash=content_hash,
        source=source,
        organization_id=str(organization_id),
        workspace_id=str(workspace_id),
        owner_user_id=user_id,
        visibility="workspace",
    )
    session.add(event)
    session.flush()
    create_context_item(session, event)
    session.commit()
    return len(chunks)
