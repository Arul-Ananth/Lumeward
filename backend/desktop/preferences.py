from __future__ import annotations

from PySide6.QtCore import QSettings

from backend.common.config import settings

_ORG_NAME = "Lumeward"
_APP_NAME = "Lumeward"

_KEY_THEME_MODE = "ui/theme_mode"
_KEY_LLM_PROVIDER = "llm/provider"
_KEY_LLM_BASE_URL = "llm/base_url"
_KEY_LLM_MODEL_NAME = "llm/model_name"
_KEY_DATA_COLLECTION_ENABLED = "telemetry/data_collection_enabled"
_KEY_CLIPBOARD_COLLECTION_ENABLED = "telemetry/clipboard_collection_enabled"
_KEY_CLIPBOARD_STORE_RAW_TEXT = "telemetry/clipboard_store_raw_text"

_VALID_THEME_MODES = {"system", "dark", "light"}
_VALID_LLM_PROVIDERS = {"ollama", "openai", "google"}


def _store() -> QSettings:
    return QSettings(_ORG_NAME, _APP_NAME)


def _to_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_theme_mode(value: str | None) -> str:
    if not value:
        return "system"
    mode = value.strip().lower()
    return mode if mode in _VALID_THEME_MODES else "system"


def _normalize_llm_provider(value: str | None) -> str:
    if not value:
        return "ollama"
    provider = value.strip().lower()
    return provider if provider in _VALID_LLM_PROVIDERS else "ollama"


def apply_llm_preferences_to_settings() -> None:
    settings.LLM_PROVIDER = get_llm_provider()
    settings.OPENAI_API_BASE = get_llm_base_url()
    settings.OPENAI_MODEL_NAME = get_llm_model_name()


def get_theme_mode() -> str:
    raw = _store().value(_KEY_THEME_MODE, "system")
    return _normalize_theme_mode(raw if isinstance(raw, str) else str(raw))


def set_theme_mode(mode: str) -> None:
    _store().setValue(_KEY_THEME_MODE, _normalize_theme_mode(mode))


def get_llm_provider() -> str:
    raw = _store().value(_KEY_LLM_PROVIDER, settings.LLM_PROVIDER or "ollama")
    return _normalize_llm_provider(raw if isinstance(raw, str) else str(raw))


def set_llm_provider(provider: str) -> None:
    _store().setValue(_KEY_LLM_PROVIDER, _normalize_llm_provider(provider))


def get_llm_base_url() -> str:
    default = settings.OPENAI_API_BASE or "http://localhost:11434"
    raw = _store().value(_KEY_LLM_BASE_URL, default)
    value = raw if isinstance(raw, str) else str(raw)
    return value.strip() or default


def set_llm_base_url(base_url: str) -> None:
    _store().setValue(_KEY_LLM_BASE_URL, base_url.strip() or "http://localhost:11434")


def get_llm_model_name() -> str:
    raw = _store().value(_KEY_LLM_MODEL_NAME, settings.OPENAI_MODEL_NAME or "mistral:latest")
    value = raw if isinstance(raw, str) else str(raw)
    return value.strip() or "mistral:latest"


def set_llm_model_name(model_name: str) -> None:
    _store().setValue(_KEY_LLM_MODEL_NAME, model_name.strip() or "mistral:latest")


def get_data_collection_enabled() -> bool:
    raw = _store().value(_KEY_DATA_COLLECTION_ENABLED, None)
    return _to_bool(raw, settings.DATA_COLLECTION_ENABLED)


def set_data_collection_enabled(enabled: bool) -> None:
    _store().setValue(_KEY_DATA_COLLECTION_ENABLED, bool(enabled))


def get_clipboard_collection_enabled() -> bool:
    raw = _store().value(_KEY_CLIPBOARD_COLLECTION_ENABLED, None)
    return _to_bool(raw, settings.CLIPBOARD_COLLECTION_ENABLED)


def set_clipboard_collection_enabled(enabled: bool) -> None:
    _store().setValue(_KEY_CLIPBOARD_COLLECTION_ENABLED, bool(enabled))


def get_clipboard_store_raw_text_enabled() -> bool:
    raw = _store().value(_KEY_CLIPBOARD_STORE_RAW_TEXT, None)
    return _to_bool(raw, settings.CLIPBOARD_STORE_RAW_TEXT)


def set_clipboard_store_raw_text_enabled(enabled: bool) -> None:
    _store().setValue(_KEY_CLIPBOARD_STORE_RAW_TEXT, bool(enabled))
