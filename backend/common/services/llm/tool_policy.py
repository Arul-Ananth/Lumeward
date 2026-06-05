from backend.common.config import settings
from backend.common.services.llm.provider_factory import allow_search_fallback


def resolve_search_mode(api_keys: dict | None = None) -> str:
    keys = api_keys or {}
    serper_key = keys.get("serper_api_key") or settings.SERPER_API_KEY
    fallback = allow_search_fallback()
    if serper_key:
        return "serper"
    if fallback:
        return "fallback"
    return "disabled"


def describe_search_mode(api_keys: dict | None = None) -> str:
    mode = resolve_search_mode(api_keys=api_keys)
    if mode == "serper":
        return "Serper web search enabled."
    if mode == "fallback":
        return "Fallback web search enabled."
    return "Web search unavailable."


def build_search_tools(api_keys: dict | None = None) -> list:
    from backend.common.services.search.web_search import WebSearchGoogleTool, WebSearchTool

    keys = api_keys or {}
    serper_key = keys.get("serper_api_key") or settings.SERPER_API_KEY
    fallback = allow_search_fallback()

    if not serper_key and not fallback:
        return []

    return [
        WebSearchTool(serper_api_key=serper_key, allow_fallback=fallback),
        WebSearchGoogleTool(serper_api_key=serper_key, allow_fallback=fallback),
    ]
