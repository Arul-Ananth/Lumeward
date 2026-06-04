from __future__ import annotations

import logging
import time

from crewai import LLM

from backend.common.config import AppMode, settings
from backend.common.services.network import build_request_headers, build_retry_session
from backend.common.services.security_policy import audit_policy_decision, authorize_network_action

logger = logging.getLogger(__name__)

_ENGINE_READY_CACHE: dict[str, object] = {
    "base_url": "",
    "checked_at": 0.0,
    "ok": False,
}
_ENGINE_CACHE_TTL_SECONDS = 30.0


def _build_remote_engine_llm() -> LLM:
    model, base_url, api_key = _resolve_remote_engine_config()
    check_remote_engine_ready()
    return LLM(
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout=settings.ENGINE_TIMEOUT_SECONDS,
        temperature=0.7,
        max_retries=settings.ENGINE_MAX_RETRIES,
    )


def _resolve_remote_engine_config() -> tuple[str, str, str]:
    model = settings.engine_model_name()
    base_url = settings.engine_base_url()
    api_key = settings.ENGINE_API_KEY.strip()
    if not base_url:
        raise ValueError("ENGINE_BASE_URL is required when ENGINE_ENABLED=true.")
    if not api_key:
        raise ValueError("ENGINE_API_KEY is required when ENGINE_ENABLED=true.")
    if not model:
        raise ValueError("ENGINE_MODEL_NAME or OPENAI_MODEL_NAME is required when ENGINE_ENABLED=true.")
    return model, base_url, api_key


def _engine_models_url() -> str:
    base_url = settings.engine_base_url()
    if not base_url:
        return ""
    return f"{base_url}/models"


def check_remote_engine_ready(*, force: bool = False, log_only: bool = False) -> bool:
    if not settings.ENGINE_ENABLED:
        return False

    _resolve_remote_engine_config()
    base_url = settings.engine_base_url()
    cached_base = str(_ENGINE_READY_CACHE["base_url"])
    checked_at = float(_ENGINE_READY_CACHE["checked_at"])
    cache_ok = bool(_ENGINE_READY_CACHE["ok"])
    now = time.time()
    if not force and cached_base == base_url and cache_ok and now - checked_at < _ENGINE_CACHE_TTL_SECONDS:
        return True

    target = _engine_models_url()
    decision = authorize_network_action("engine.health", target)
    audit_policy_decision(decision=decision, tool_name="Remote Engine", query="readiness check")
    if not decision.allowed:
        message = f"Remote engine blocked by security policy: {decision.reason}"
        if log_only:
            logger.warning(message)
            return False
        raise RuntimeError(message)

    session = build_retry_session(settings.ENGINE_MAX_RETRIES)
    headers = build_request_headers(
        {
            "Authorization": f"Bearer {settings.ENGINE_API_KEY.strip()}",
            "X-Lumeward-Client": settings.APP_MODE.value.lower(),
        }
    )

    try:
        response = session.get(target, headers=headers, timeout=(5, settings.ENGINE_TIMEOUT_SECONDS))
        response.raise_for_status()
    except Exception as exc:
        _ENGINE_READY_CACHE.update({"base_url": base_url, "checked_at": now, "ok": False})
        message = f"Remote engine readiness check failed for {target}: {exc}"
        if log_only:
            logger.warning(message)
            return False
        raise RuntimeError(message) from exc

    _ENGINE_READY_CACHE.update({"base_url": base_url, "checked_at": now, "ok": True})
    return True


def is_remote_engine_enabled() -> bool:
    return settings.ENGINE_ENABLED


def build_llm(api_keys: dict | None = None) -> LLM:
    if settings.ENGINE_ENABLED:
        return _build_remote_engine_llm()

    keys = api_keys or {}
    provider = (settings.LLM_PROVIDER or "").strip().lower()
    if not provider:
        raise ValueError("LLM_PROVIDER is not set. Use 'ollama', 'openai', or 'google' in .env.")

    if provider == "openai":
        openai_key = keys.get("openai_api_key") or settings.OPENAI_API_KEY
        if not openai_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        model = settings.OPENAI_MODEL_NAME
        base_url = settings.OPENAI_API_BASE or "https://api.openai.com/v1"
        api_key = openai_key
    elif provider == "google":
        gemini_key = keys.get("gemini_api_key") or settings.GEMINI_API_KEY
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=google.")
        model = settings.OPENAI_MODEL_NAME
        base_url = settings.OPENAI_API_BASE or ""
        api_key = gemini_key
    elif provider == "ollama":
        model = f"ollama/{settings.OPENAI_MODEL_NAME.split(':')[0]}"
        base_url = settings.OPENAI_API_BASE or "http://localhost:11434"
        api_key = "NA"
    else:
        raise ValueError("LLM_PROVIDER must be 'ollama', 'openai', or 'google'.")

    return LLM(
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout=300,
        temperature=0.7,
    )


def allow_search_fallback() -> bool:
    if settings.APP_MODE == AppMode.DESKTOP:
        return True
    return settings.ALLOW_SERVER_DDG_FALLBACK
