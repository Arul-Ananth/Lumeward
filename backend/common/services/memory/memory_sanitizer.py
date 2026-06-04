from backend.common.security.policy import InputSanitizer

_sanitizer = InputSanitizer()


def sanitize_memory_context(text: str) -> str:
    return _sanitizer.sanitize_context(text)
