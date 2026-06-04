"""Compatibility helpers for older newsletter crew callers.

The active newsletter path uses ``newsletter_service`` and ``tool_policy``
directly. Keep this module as a thin import surface for manual scripts or
external callers that still use ``run_newsletter_crew``.
"""

from typing import Any, Type, Union

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from backend.common.services.llm.crew_builder import build_newsletter_crew
from backend.common.services.llm.provider_factory import build_llm
from backend.common.services.llm.tool_policy import build_search_tools
from backend.common.services.search.web_search import WebSearchGoogleTool, WebSearchTool


class SearchToolInput(BaseModel):
    query: Union[str, dict] = Field(..., description="The search topic. Example: 'climate change'")


class CrewWebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = "Search the internet for facts."
    args_schema: Type[BaseModel] = SearchToolInput

    def __init__(self, serper_api_key: str | None = None, allow_fallback: bool | None = None):
        super().__init__()
        self._inner = WebSearchTool(serper_api_key=serper_api_key, allow_fallback=allow_fallback)

    def _run(self, query: Union[str, dict]) -> str:
        return self._inner.run(query)


class CrewWebSearchGoogleTool(BaseTool):
    name: str = "Web Search (Google)"
    description: str = "Search the internet for facts."
    args_schema: Type[BaseModel] = SearchToolInput

    def __init__(self, serper_api_key: str | None = None, allow_fallback: bool | None = None):
        super().__init__()
        self._inner = WebSearchGoogleTool(serper_api_key=serper_api_key, allow_fallback=allow_fallback)

    def _run(self, query: Union[str, dict]) -> str:
        return self._inner.run(query)


search_tool = CrewWebSearchTool()


def run_newsletter_crew(topic: str, user_context: str, api_keys: dict | None = None) -> Any:
    llm = build_llm(api_keys=api_keys or {})
    tools = build_search_tools(api_keys=api_keys or {})
    crew = build_newsletter_crew(topic=topic, context=user_context, llm=llm, tools=tools)
    return crew.kickoff()
