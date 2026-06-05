"""Compatibility helpers for older newsletter crew callers.

The active newsletter path uses ``backend.common.services.newsletter``. Keep
this module as a thin import surface for manual scripts or external callers
that still use ``run_newsletter_crew``.
"""

from typing import Any

from backend.common.services.llm.crew_builder import build_newsletter_crew
from backend.common.services.llm.provider_factory import build_llm
from backend.common.services.llm.tool_policy import build_search_tools
from backend.common.services.search.web_search import (
    SearchToolInput,
    WebSearchGoogleTool as CrewWebSearchGoogleTool,
    WebSearchTool as CrewWebSearchTool,
)


search_tool = CrewWebSearchTool()


def run_newsletter_crew(topic: str, user_context: str, api_keys: dict | None = None) -> Any:
    llm = build_llm(api_keys=api_keys or {})
    tools = build_search_tools(api_keys=api_keys or {})
    crew = build_newsletter_crew(topic=topic, context=user_context, llm=llm, tools=tools)
    return crew.kickoff()
