import json
import logging
import re
import threading
from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ApiException, ResponseHandlingException
from qdrant_client.http import models
from sqlmodel import Session, select

from backend.common.config import AppMode, settings
from backend.common.database import session_scope
from backend.common.models.sql import EventRaw
from backend.common.services.memory.point_ids import stable_point_id

logger = logging.getLogger(__name__)


class QdrantUnavailableError(RuntimeError):
    """Raised when server-mode Qdrant storage cannot complete an operation."""


_QDRANT_CONNECTION_ERRORS = (ApiException, ResponseHandlingException, ConnectionError, OSError, TimeoutError)
_embedder: Any | None = None
_embedder_lock = threading.Lock()
_client: QdrantClient | None = None
_client_lock = threading.Lock()
_CLIPBOARD_QUERY_PATTERNS = (
    "clipboard",
    "what did i just copy",
    "what i just copy",
    "copied to clipboard",
    "clipboard history",
)
_CLIPBOARD_STOPWORDS = {
    "tell",
    "me",
    "what",
    "did",
    "i",
    "just",
    "copy",
    "copied",
    "to",
    "clipboard",
    "history",
    "from",
    "my",
    "know",
    "about",
    "the",
}


def _create_client() -> QdrantClient:
    if settings.APP_MODE == AppMode.DESKTOP:
        return QdrantClient(path=str(settings.DATA_DIR / "qdrant_db"))
    if not settings.QDRANT_URL.strip():
        raise RuntimeError("Server mode requires QDRANT_URL; embedded Qdrant is desktop-only.")
    return QdrantClient(
        url=settings.QDRANT_URL.strip(),
        api_key=settings.QDRANT_API_KEY.strip() or None,
        timeout=settings.QDRANT_TIMEOUT_SECONDS,
        prefer_grpc=settings.QDRANT_PREFER_GRPC,
    )


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = _create_client()
    return _client


class _LazyQdrantClient:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_client(), name)

    def close(self) -> None:
        if _client is not None:
            _client.close()


client = _LazyQdrantClient()


def get_embedder() -> Any:
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                from sentence_transformers import SentenceTransformer

                _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def ensure_collection(name: str) -> None:
    qdrant_client = get_client()
    if qdrant_client.collection_exists(name):
        return
    try:
        qdrant_client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=384,
                distance=models.Distance.COSINE,
            ),
        )
    except Exception:
        if not qdrant_client.collection_exists(name):
            raise


def check_qdrant_ready() -> None:
    try:
        get_client().get_collections()
    except _QDRANT_CONNECTION_ERRORS as exc:
        url = settings.QDRANT_URL.strip()
        raise QdrantUnavailableError(
            f"Qdrant is unavailable at {url}. Start the external service or use QDRANT_MODE=bundled."
        ) from exc


def initialize_qdrant_collections() -> None:
    for collection in (
        settings.QDRANT_COLLECTION_USER_DOCS,
        settings.QDRANT_COLLECTION_SESSION_MEMORY,
        settings.QDRANT_COLLECTION_USER_PROFILE,
    ):
        ensure_collection(collection)


def close_qdrant() -> None:
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
        _client = None


def _query_collection(
    collection: str,
    user_id: int,
    query: str,
    limit: int = 3,
    workspace_ids: tuple[int, ...] = (),
    organization_ids: tuple[int, ...] = (),
) -> list[str]:
    try:
        ensure_collection(collection)
    except _QDRANT_CONNECTION_ERRORS as exc:
        return _handle_qdrant_unavailable("ensure collection", collection, exc, [])

    query_vector = get_embedder().encode(query).tolist()
    try:
        results = client.query_points(
            collection_name=collection,
            query=query_vector,
            query_filter=_scope_filter(user_id, workspace_ids, organization_ids),
            limit=limit,
        ).points
        return [hit.payload.get("document", "") for hit in results if hit.payload.get("document")]
    except _QDRANT_CONNECTION_ERRORS as exc:
        return _handle_qdrant_unavailable("query", collection, exc, [])


def get_user_context(user_id: int, topic: str, workspace_ids: tuple[int, ...] = (), organization_ids: tuple[int, ...] = ()) -> str:
    documents = _query_collection(
        settings.QDRANT_COLLECTION_USER_PROFILE,
        user_id,
        topic,
        limit=3,
        workspace_ids=workspace_ids,
        organization_ids=organization_ids,
    )
    return "\n".join(documents) if documents else "No specific preferences found."


def save_feedback(user_id: int, topic: str, feedback: str, sentiment: str) -> None:
    collection = settings.QDRANT_COLLECTION_USER_PROFILE
    try:
        ensure_collection(collection)
    except _QDRANT_CONNECTION_ERRORS as exc:
        _handle_qdrant_unavailable("ensure collection", collection, exc, None)
        return

    text = f"Topic: {topic}. User Feedback: {feedback}. Sentiment: {sentiment}"
    vector = get_embedder().encode(text).tolist()
    point_id = stable_point_id("feedback", user_id, topic, feedback, sentiment)

    try:
        client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document": text,
                        "user_id": str(user_id),
                        "topic": topic,
                        "sentiment": sentiment,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            ],
        )
    except _QDRANT_CONNECTION_ERRORS as exc:
        _handle_qdrant_unavailable("upsert", collection, exc, None)


def fetch_memories(user_id: int):
    collection = settings.QDRANT_COLLECTION_USER_PROFILE
    try:
        ensure_collection(collection)
        response = client.scroll(
            collection_name=collection,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=str(user_id)),
                    )
                ]
            ),
            limit=100,
        )

        points, _ = response
        return [
            {
                "id": point.id,
                "document": point.payload.get("document", ""),
                "metadata": point.payload,
            }
            for point in points
        ]
    except _QDRANT_CONNECTION_ERRORS as exc:
        return _handle_qdrant_unavailable("scroll", collection, exc, [])


def _handle_qdrant_unavailable(operation: str, collection: str, exc: Exception, desktop_fallback):
    logger.error(
        "Qdrant operation failed",
        extra={
            "qdrant_operation": operation,
            "qdrant_collection": collection,
            "error_type": type(exc).__name__,
        },
        exc_info=True,
    )
    if settings.APP_MODE == AppMode.SERVER:
        raise QdrantUnavailableError(
            f"Qdrant unavailable during {operation} for collection {collection}."
        ) from exc
    return desktop_fallback


def get_memory_context(
    user_id: int,
    topic: str,
    session_id: str | None = None,
    workspace_ids: tuple[int, ...] = (),
    organization_ids: tuple[int, ...] = (),
) -> str:
    sections: list[str] = []

    user_docs = _query_collection(settings.QDRANT_COLLECTION_USER_DOCS, user_id, topic, limit=5, workspace_ids=workspace_ids, organization_ids=organization_ids)
    if user_docs:
        sections.append("User Documents:\n" + "\n".join(user_docs))

    session_mem = _query_collection(settings.QDRANT_COLLECTION_SESSION_MEMORY, user_id, topic, limit=3, workspace_ids=workspace_ids, organization_ids=organization_ids)
    if session_mem:
        sections.append("Session Memory:\n" + "\n".join(session_mem))

    profile = _query_collection(settings.QDRANT_COLLECTION_USER_PROFILE, user_id, topic, limit=3, workspace_ids=workspace_ids, organization_ids=organization_ids)
    if profile:
        sections.append("User Profile:\n" + "\n".join(profile))

    return "\n\n".join(sections).strip()


def _scope_filter(user_id: int, workspace_ids: tuple[int, ...], organization_ids: tuple[int, ...]):
    scopes = [models.Filter(
        must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id)))],
        must_not=[models.FieldCondition(key="visibility", match=models.MatchAny(any=["workspace", "organization"]))],
    )]
    if workspace_ids:
        scopes.append(models.Filter(must=[
            models.FieldCondition(key="workspace_id", match=models.MatchAny(any=[str(value) for value in workspace_ids])),
            models.FieldCondition(key="visibility", match=models.MatchValue(value="workspace")),
        ]))
    if organization_ids:
        scopes.append(models.Filter(must=[
            models.FieldCondition(key="organization_id", match=models.MatchAny(any=[str(value) for value in organization_ids])),
            models.FieldCondition(key="visibility", match=models.MatchValue(value="organization")),
        ]))
    return models.Filter(should=scopes)


def is_clipboard_history_query(topic: str) -> bool:
    lowered = topic.strip().lower()
    return any(pattern in lowered for pattern in _CLIPBOARD_QUERY_PATTERNS)


def get_recent_clipboard_context(topic: str, session_id: str | None = None, limit: int = 5) -> str:
    if not is_clipboard_history_query(topic):
        return ""

    terms = _clipboard_query_terms(topic)
    matches = _matching_clipboard_entries(terms=terms, session_id=session_id, limit=limit)
    if not matches:
        if terms:
            return (
                "Clipboard History Context:\n"
                f"- No recent clipboard entries matched: {', '.join(terms)}"
            )
        latest = _matching_clipboard_entries(terms=[], session_id=session_id, limit=1)
        if latest:
            return "Clipboard History Context:\n" + "\n".join(f"- {item}" for item in latest)
        return "Clipboard History Context:\n- No recent clipboard entries were captured."

    return "Clipboard History Context:\n" + "\n".join(f"- {item}" for item in matches)


def _clipboard_query_terms(topic: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9_+-]+", topic.lower())
    filtered = [token for token in tokens if token not in _CLIPBOARD_STOPWORDS and len(token) > 2]
    seen: list[str] = []
    for token in filtered:
        if token not in seen:
            seen.append(token)
    return seen


def _matching_clipboard_entries(terms: list[str], session_id: str | None, limit: int) -> list[str]:
    entries: list[str] = []
    seen_text: set[str] = set()

    def add_matches(records: list[EventRaw]) -> None:
        for event in records:
            payload = json.loads(event.payload_json)
            text = (payload.get("text") or payload.get("url") or "").strip()
            if not text:
                continue
            lowered = text.lower()
            if terms and not any(term in lowered for term in terms):
                continue
            normalized = text[:1200]
            if normalized in seen_text:
                continue
            seen_text.add(normalized)
            entries.append(normalized)
            if len(entries) >= limit:
                break

    with session_scope() as session:
        if session_id:
            current_session = session.exec(
                select(EventRaw)
                .where(EventRaw.event_type == "clipboard", EventRaw.session_id == session_id)
                .order_by(EventRaw.ts.desc())
            ).all()
            add_matches(current_session)

        if len(entries) < limit:
            recent = session.exec(
                select(EventRaw)
                .where(EventRaw.event_type == "clipboard")
                .order_by(EventRaw.ts.desc())
            ).all()
            add_matches(recent)

    return entries[:limit]
