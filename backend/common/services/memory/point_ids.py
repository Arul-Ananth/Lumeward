"""Deterministic Qdrant point identifiers for idempotent writes."""
import hashlib
import uuid


def stable_point_id(*parts: object) -> str:
    value = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))
