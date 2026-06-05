from typing import Type, Union
import warnings

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from backend.common.config import AppMode, settings
from backend.common.services.network import build_request_headers, build_retry_session
from backend.common.services.security_policy import audit_policy_decision, authorize_network_action

SERPER_URL = "https://google.serper.dev/search"
FALLBACK_DISCOVERY_URL = "https://duckduckgo.com"


class SearchToolInput(BaseModel):
    query: Union[str, dict] = Field(..., description="The search topic.")


def _normalize_query(query: Union[str, dict]) -> str:
    if isinstance(query, dict):
        return str(query.get("description", str(query)))
    return str(query)


class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = "Search the internet for facts."
    args_schema: Type[BaseModel] = SearchToolInput

    def __init__(self, serper_api_key: str | None = None, allow_fallback: bool | None = None):
        super().__init__()
        self._serper_api_key = serper_api_key or ""
        if allow_fallback is None:
            allow_fallback = settings.APP_MODE == AppMode.DESKTOP
        self._allow_fallback = allow_fallback
        self._http = build_retry_session()

    def _run(self, query: Union[str, dict]) -> str:
        normalized = _normalize_query(query)
        if self._serper_api_key:
            return self._serper_search(normalized)
        if self._allow_fallback:
            return self._duckduckgo_scrape(normalized)
        return "Web search unavailable: missing Serper API key."

    def _serper_search(self, query: str) -> str:
        decision = authorize_network_action("search.serper", SERPER_URL)
        audit_policy_decision(decision=decision, tool_name=self.name, query=query)
        if not decision.allowed:
            return f"Search blocked by security policy: {decision.reason}"

        headers = {
            "X-API-KEY": self._serper_api_key,
            "Content-Type": "application/json",
        }
        headers = build_request_headers(headers)
        payload = {"q": query}

        try:
            response = self._http.post(SERPER_URL, headers=headers, json=payload, timeout=(5, 15))
            response.raise_for_status()
            results = response.json()
        except Exception as exc:
            return f"Error executing search: {exc}"

        organic = results.get("organic") or []
        if not organic:
            return "No results."
        lines = [f"- {item.get('title', '')}: {item.get('snippet', '')}" for item in organic[:3]]
        return "\n".join(lines)

    def _duckduckgo_scrape(self, query: str) -> str:
        try:
            import trafilatura
            DDGS, backend_options = _load_fallback_search_client()
        except Exception as exc:
            return f"Fallback search unavailable: {exc}"

        discovery_decision = authorize_network_action("search.discovery", FALLBACK_DISCOVERY_URL)
        audit_policy_decision(decision=discovery_decision, tool_name=self.name, query=query)
        if not discovery_decision.allowed:
            return f"Search blocked by security policy: {discovery_decision.reason}"

        try:
            results = []
            errors = []
            for search_kwargs in backend_options:
                ddgs = DDGS(timeout=10)
                try:
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message=r"This package \(`duckduckgo_search`\) has been renamed to `ddgs`!.*",
                            category=RuntimeWarning,
                        )
                        results = list(ddgs.text(query, max_results=5, **search_kwargs))
                except Exception as exc:
                    errors.append(f"{search_kwargs}: {exc}")
                finally:
                    close = getattr(ddgs, "close", None)
                    if callable(close):
                        close()
                if results:
                    break
            if not results:
                detail = "; ".join(errors) if errors else "No results."
                return f"Error executing fallback search: {detail}"
        except Exception as exc:
            return f"Error executing fallback search: {exc}"

        urls = [item.get("href") for item in results if item.get("href")]
        if not urls:
            return "No results."

        texts = []
        for url in urls[:3]:
            text = self._fetch_and_extract(url, trafilatura, query)
            if text:
                texts.append(text[:4000])

        if not texts:
            snippets = [
                f"- {item.get('title', '')}: {item.get('body') or item.get('snippet', '')}"
                for item in results[:3]
            ]
            return "\n".join(line for line in snippets if line.strip(" -:"))
        return "\n\n".join(texts)

    def _fetch_and_extract(self, url: str, trafilatura_module, query: str) -> str:
        decision = authorize_network_action("search.fetch", url)
        audit_policy_decision(decision=decision, tool_name=self.name, query=query)
        if not decision.allowed:
            return ""

        try:
            response = self._http.get(url, timeout=(5, 15), headers=build_request_headers())
            response.raise_for_status()
        except Exception:
            return ""

        extracted = trafilatura_module.extract(response.text)
        return extracted or ""


class WebSearchGoogleTool(WebSearchTool):
    name: str = "Web Search (Google)"
    description: str = "Search the internet for facts."


def _load_fallback_search_client():
    try:
        from ddgs import DDGS

        return DDGS, [
            {"backend": "duckduckgo"},
            {"backend": "html"},
            {"backend": "lite"},
        ]
    except Exception as ddgs_exc:
        try:
            from duckduckgo_search import DDGS

            return DDGS, [{"backend": "html"}]
        except Exception as legacy_exc:
            raise RuntimeError(f"ddgs import failed: {ddgs_exc}; duckduckgo_search import failed: {legacy_exc}")
