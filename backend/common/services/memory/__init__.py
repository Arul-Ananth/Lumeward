from backend.common.services.memory.memory_sanitizer import sanitize_memory_context

__all__ = [
    "sanitize_memory_context",
    "client",
    "ensure_collection",
    "fetch_memories",
    "get_embedder",
    "get_memory_context",
    "get_user_context",
    "save_feedback",
]


def __getattr__(name: str):
    if name in {
        "client",
        "ensure_collection",
        "fetch_memories",
        "get_embedder",
        "get_memory_context",
        "get_user_context",
        "save_feedback",
    }:
        from backend.common.services.memory import vector_db

        return getattr(vector_db, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
