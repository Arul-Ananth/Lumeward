from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from qdrant_client.http import models
from sqlmodel import Session, select

from backend.common.config import settings
from backend.common.database import session_scope
from backend.common.models.sql import DerivedMemory, EventRaw, FilesIndex
from backend.common.services.telemetry.event_bus import EventBus, TelemetryEvent
from backend.common.services.telemetry.ingestion import chunk_text, extract_text_from_file, file_sha256
from backend.common.services.memory.vector_db import client, ensure_collection, get_embedder
from backend.common.services.memory.point_ids import stable_point_id

logger = logging.getLogger(__name__)


class _AsyncQueueWorker:
    def __init__(self, queue: asyncio.Queue, error_label: str) -> None:
        self.queue = queue
        self._error_label = error_label
        self._stop = asyncio.Event()

    async def run(self) -> None:
        while not self._stop.is_set():
            event = await self.queue.get()
            try:
                await self._process_event(event)
            except Exception as exc:
                logger.exception("%s error: %s", self._error_label, exc)
            finally:
                self.queue.task_done()

    def stop(self) -> None:
        self._stop.set()

    async def _process_event(self, event: TelemetryEvent) -> None:
        raise NotImplementedError


class TelemetryDispatcher(_AsyncQueueWorker):
    def __init__(self, event_bus: EventBus, ingestion_queue: asyncio.Queue, summary_queue: asyncio.Queue) -> None:
        super().__init__(event_bus.queue, "Telemetry dispatcher")
        self.event_bus = event_bus
        self.ingestion_queue = ingestion_queue
        self.summary_queue = summary_queue
        self._writes = 0

    async def _process_event(self, event: TelemetryEvent) -> None:
        self._persist_event(event)
        if event.event_type == "file_ingestion":
            await self.ingestion_queue.put(event)
        if event.event_type in {"session_end", "generate_newsletter"}:
            await self.summary_queue.put(event)

    def _persist_event(self, event: TelemetryEvent) -> None:
        content_hash = event.content_hash or _hash_payload(event)
        with session_scope() as session:
            if _is_duplicate(session, content_hash):
                logger.info("Skipping duplicate event: %s", event.event_type)
                return

            raw = EventRaw(
                event_type=event.event_type,
                ts=event.ts,
                session_id=event.session_id,
                payload_json=json.dumps(event.payload),
                hash=content_hash,
                source=event.source,
            )
            session.add(raw)
            session.commit()

        self._writes += 1
        if self._writes % 50 == 0:
            _purge_old_events()


class DocumentIngestionWorker(_AsyncQueueWorker):
    def __init__(self, queue: asyncio.Queue) -> None:
        super().__init__(queue, "Document ingestion")

    async def _process_event(self, event: TelemetryEvent) -> None:
        path = Path(event.payload.get("path", ""))
        user_id = event.payload.get("user_id")
        if not path.exists() or not user_id:
            logger.warning("Invalid file ingestion event: %s", event.payload)
            return

        max_bytes = settings.DOC_MAX_MB * 1024 * 1024
        if path.stat().st_size > max_bytes:
            _update_file_index(path, "error", "File exceeds size limit")
            return

        content_hash = file_sha256(path)
        mtime = path.stat().st_mtime

        with session_scope() as session:
            existing = session.get(FilesIndex, str(path))
            if existing and existing.content_hash == content_hash and existing.mtime == mtime:
                _update_file_index(path, "skipped", "Unchanged file", content_hash, mtime)
                return

        text, error = extract_text_from_file(path)
        if error:
            _update_file_index(path, "error", error)
            return

        chunks = chunk_text(text or "", settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        if not chunks:
            _update_file_index(path, "error", "No text extracted")
            return

        ensure_collection(settings.QDRANT_COLLECTION_USER_DOCS)
        vectors = get_embedder().encode(chunks).tolist()
        points = []
        for idx, vector in enumerate(vectors):
            points.append(
                models.PointStruct(
                    id=stable_point_id("document", user_id, content_hash, idx),
                    vector=vector,
                    payload={
                        "document": chunks[idx],
                        "user_id": str(user_id),
                        "path": str(path),
                        "chunk_index": idx,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            )

        client.upsert(collection_name=settings.QDRANT_COLLECTION_USER_DOCS, points=points)
        _update_file_index(path, "ingested", None, content_hash, mtime)


class SessionSummaryWorker(_AsyncQueueWorker):
    def __init__(self, queue: asyncio.Queue, profile_worker: "UserProfileRollupWorker") -> None:
        super().__init__(queue, "Session summary")
        self.profile_worker = profile_worker

    async def _process_event(self, event: TelemetryEvent) -> None:
        summary = _build_session_summary(event.session_id)
        if not summary:
            return
        user_id = _coerce_user_id(event.payload.get("user_id"))

        ensure_collection(settings.QDRANT_COLLECTION_SESSION_MEMORY)
        vector = get_embedder().encode(summary).tolist()
        point_id = stable_point_id("session-summary", user_id, event.session_id)

        client.upsert(
            collection_name=settings.QDRANT_COLLECTION_SESSION_MEMORY,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document": summary,
                        "user_id": str(user_id) if user_id >= 0 else "",
                        "session_id": event.session_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            ],
        )

        with session_scope() as session:
            memory = DerivedMemory(
                user_id=user_id,
                memory_type="session_summary",
                source_refs=json.dumps({"session_id": event.session_id, "event_type": event.event_type}),
                summary_text=summary,
                qdrant_point_id=point_id,
            )
            session.add(memory)
            session.commit()

        if user_id >= 0:
            await self.profile_worker.maybe_rollup(user_id)


class UserProfileRollupWorker:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def maybe_rollup(self, user_id: int | None) -> None:
        resolved_user_id = _coerce_user_id(user_id)
        if resolved_user_id < 0:
            return
        async with self._lock:
            with session_scope() as session:
                summary_count = session.exec(
                    select(DerivedMemory)
                    .where(
                        DerivedMemory.memory_type == "session_summary",
                        DerivedMemory.user_id == resolved_user_id,
                    )
                    .order_by(DerivedMemory.ts)
                ).all()
                profile_count = session.exec(
                    select(DerivedMemory).where(
                        DerivedMemory.memory_type == "user_profile",
                        DerivedMemory.user_id == resolved_user_id,
                    )
                ).all()

            if len(summary_count) < settings.PROFILE_ROLLUP_EVERY:
                return
            if len(summary_count) < (len(profile_count) + 1) * settings.PROFILE_ROLLUP_EVERY:
                return

            summary_texts = [m.summary_text for m in summary_count[-settings.PROFILE_ROLLUP_EVERY :]]
            profile_text = "User profile rollup:\n" + "\n".join(summary_texts)

            ensure_collection(settings.QDRANT_COLLECTION_USER_PROFILE)
            vector = get_embedder().encode(profile_text).tolist()
            point_id = stable_point_id("profile-rollup", resolved_user_id, len(profile_count) + 1)

            client.upsert(
                collection_name=settings.QDRANT_COLLECTION_USER_PROFILE,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "document": profile_text,
                            "user_id": str(resolved_user_id),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                ],
            )

            with session_scope() as session:
                memory = DerivedMemory(
                    user_id=resolved_user_id,
                    memory_type="user_profile",
                    source_refs=json.dumps({"rollup": settings.PROFILE_ROLLUP_EVERY}),
                    summary_text=profile_text,
                    qdrant_point_id=point_id,
                )
                session.add(memory)
                session.commit()


def _hash_payload(event: TelemetryEvent) -> str:
    payload = {
        "event_type": event.event_type,
        "session_id": event.session_id,
        "payload": event.payload,
        "source": event.source,
        "priority": event.priority.name,
        "ts": event.ts.isoformat(),
    }
    raw = json.dumps(payload, sort_keys=True)
    return uuid.uuid5(uuid.NAMESPACE_DNS, raw).hex


def _coerce_user_id(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _is_duplicate(session: Session, content_hash: str) -> bool:
    cutoff = datetime.utcnow() - timedelta(seconds=settings.DEDUPE_WINDOW_SECONDS)
    statement = select(EventRaw).where(EventRaw.hash == content_hash, EventRaw.ts >= cutoff)
    return session.exec(statement).first() is not None


def _purge_old_events() -> None:
    cutoff = datetime.utcnow() - timedelta(days=settings.RETENTION_DAYS_EVENTS_RAW)
    with session_scope() as session:
        events = session.exec(select(EventRaw).where(EventRaw.ts < cutoff)).all()
        for event in events:
            session.delete(event)
        session.commit()


def _update_file_index(path: Path, status: str, error: str | None, content_hash: str | None = None, mtime: float | None = None) -> None:
    with session_scope() as session:
        record = session.get(FilesIndex, str(path))
        if record is None:
            record = FilesIndex(path=str(path), content_hash=content_hash or "", mtime=mtime or 0)
        record.status = status
        record.error = error
        if content_hash is not None:
            record.content_hash = content_hash
        if mtime is not None:
            record.mtime = mtime
        record.last_ingested_at = datetime.utcnow()
        session.add(record)
        session.commit()


def _build_session_summary(session_id: str) -> str:
    with session_scope() as session:
        events = session.exec(
            select(EventRaw).where(EventRaw.session_id == session_id).order_by(EventRaw.ts)
        ).all()

    if not events:
        return ""

    topics = []
    clipboard_items = []
    file_events = []
    telemetry = Counter()
    max_scroll = 0.0
    total_output_time = 0.0

    for event in events:
        payload = json.loads(event.payload_json)
        if event.event_type == "generate_newsletter":
            topics.append(payload.get("topic", ""))
        if event.event_type == "clipboard":
            text = payload.get("text", "")
            if text:
                clipboard_items.append(text[:200])
            elif payload.get("content_hash"):
                clipboard_items.append(f"hash:{payload['content_hash'][:12]}")
        if event.event_type == "file_ingestion":
            file_events.append(payload.get("path", ""))
        if event.event_type == "telemetry_scroll":
            telemetry["scroll"] += 1
            max_scroll = max(max_scroll, float(payload.get("depth", 0.0)))
        if event.event_type == "telemetry_output_time":
            total_output_time += float(payload.get("seconds", 0.0))
        if event.event_type == "telemetry_copy":
            telemetry["copy"] += 1

    summary_lines = [
        f"Session {session_id} summary:",
        f"- Topics generated: {', '.join(t for t in topics if t) or 'none'}",
        f"- Clipboard highlights: {', '.join(clipboard_items[:3]) or 'none'}",
        f"- Files ingested: {', '.join(file_events[:5]) or 'none'}",
        f"- Output engagement: scroll max {max_scroll:.2f}, time {total_output_time:.1f}s, copies {telemetry['copy']}",
    ]
    return "\n".join(summary_lines)
