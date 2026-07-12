from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from qdrant_client.http import models
from sqlmodel import Session

from backend.common.config import settings
from backend.common.models.sql import EventRaw, FilesIndex
from backend.common.services.memory.point_ids import stable_point_id
from backend.common.services.memory.vector_db import client, ensure_collection, get_embedder
from backend.common.services.telemetry.ingestion import chunk_text, extract_text_from_file, file_sha256
from backend.common.services.context_items import create_context_item


class DocumentIngestionService:
    """Shared file-to-memory pipeline for uploads, watchers, and telemetry."""

    def ingest(
        self,
        session: Session,
        *,
        path: Path,
        user_id: int,
        session_id: str,
        batch_id: str = "",
        source: str = "file_ingestion",
        organization_id: str | None = None,
        workspace_id: str | None = None,
        visibility: str = "private",
        ensure_collection_fn=None,
        embedder_fn=None,
        qdrant_client=None,
    ) -> str:
        try:
            max_bytes = settings.DOC_MAX_MB * 1024 * 1024
            if path.stat().st_size > max_bytes:
                self._upsert_index(session, path, "skipped", "File exceeds size limit")
                return "skipped"

            content_hash = file_sha256(path)
            mtime = path.stat().st_mtime
            existing = session.get(FilesIndex, str(path))
            if existing and existing.content_hash == content_hash and existing.status == "ingested":
                return "skipped"

            text, error = extract_text_from_file(path)
            if error:
                self._upsert_index(session, path, "error", error, content_hash, mtime)
                return "failed"
            chunks = chunk_text(text or "", settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
            if not chunks:
                self._upsert_index(session, path, "skipped", "No text extracted", content_hash, mtime)
                return "skipped"

            (ensure_collection_fn or ensure_collection)(settings.QDRANT_COLLECTION_USER_DOCS)
            vectors = (embedder_fn or get_embedder)().encode(chunks).tolist()
            points = [
                models.PointStruct(
                    id=stable_point_id("document", user_id, content_hash, index),
                    vector=vector,
                    payload={
                        "document": chunks[index],
                        "user_id": str(user_id),
                        "organization_id": organization_id,
                        "workspace_id": workspace_id,
                        "visibility": visibility,
                        "path": str(path),
                        "chunk_index": index,
                        "upload_batch_id": batch_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                for index, vector in enumerate(vectors)
            ]
            (qdrant_client or client).upsert(collection_name=settings.QDRANT_COLLECTION_USER_DOCS, points=points)
            self._upsert_index(session, path, "ingested", None, content_hash, mtime)
            self._persist_event(
                session,
                path=path,
                user_id=user_id,
                session_id=session_id,
                content_hash=content_hash,
                source=source,
                organization_id=organization_id,
                workspace_id=workspace_id,
                visibility=visibility,
            )
            return "ingested"
        except Exception as exc:
            self._upsert_index(session, path, "error", str(exc))
            return "failed"

    @staticmethod
    def _upsert_index(
        session: Session,
        path: Path,
        status: str,
        error: str | None,
        content_hash: str | None = None,
        mtime: float | None = None,
    ) -> None:
        record = session.get(FilesIndex, str(path))
        if record is None:
            record = FilesIndex(path=str(path), content_hash=content_hash or "", mtime=mtime or 0.0)
        record.status = status
        record.error = error
        if content_hash is not None:
            record.content_hash = content_hash
        if mtime is not None:
            record.mtime = mtime
        record.last_ingested_at = datetime.utcnow()
        session.add(record)
        session.commit()

    @staticmethod
    def _persist_event(
        session: Session,
        *,
        path: Path,
        user_id: int,
        session_id: str,
        content_hash: str,
        source: str,
        organization_id: str | None,
        workspace_id: str | None,
        visibility: str,
    ) -> None:
        payload = {
            "path": str(path),
            "user_id": user_id,
            "content_hash": content_hash,
            "ts": datetime.utcnow().isoformat(),
            "consent": "folder_zip_upload" if source == "folder_upload" else source,
        }
        event = EventRaw(
            event_type="file_ingestion",
            session_id=session_id,
            payload_json=json.dumps(payload, ensure_ascii=True),
            hash=hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest(),
            source=source,
            organization_id=organization_id,
            workspace_id=workspace_id,
            owner_user_id=user_id,
            visibility=visibility,
        )
        session.add(event)
        session.flush()
        create_context_item(session, event)
        session.commit()


document_ingestion = DocumentIngestionService()
