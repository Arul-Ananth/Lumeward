import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.append(str(root))

from backend.common.config import AppMode, settings
from backend.common.services.llm.tool_policy import describe_search_mode, resolve_search_mode
from backend.common.services.search.web_search import SERPER_URL, WebSearchTool
from backend.common.services.security_policy import authorize_network_action


def _assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> int:
    original_mode = settings.APP_MODE
    original_serper = settings.SERPER_API_KEY
    original_server_fallback = settings.ALLOW_SERVER_DDG_FALLBACK

    try:
        settings.SERPER_API_KEY = ""
        settings.ALLOW_SERVER_DDG_FALLBACK = False

        settings.APP_MODE = AppMode.DESKTOP
        _assert_equal(resolve_search_mode({"serper_api_key": "abc"}), "serper", "desktop serper mode")
        _assert_equal(resolve_search_mode({}), "fallback", "desktop fallback mode")
        _assert_equal(describe_search_mode({}), "Fallback web search enabled.", "desktop mode description")

        settings.APP_MODE = AppMode.SERVER
        _assert_equal(resolve_search_mode({}), "disabled", "server disabled mode")
        _assert_equal(describe_search_mode({}), "Web search unavailable.", "server mode description")
        settings.ALLOW_SERVER_DDG_FALLBACK = True
        _assert_equal(resolve_search_mode({}), "fallback", "server explicit fallback mode")
        settings.ALLOW_SERVER_DDG_FALLBACK = False

        serper_tool = WebSearchTool(serper_api_key="abc", allow_fallback=True)
        serper_tool._serper_search = lambda query: f"SERPER:{query}"  # type: ignore[method-assign]
        serper_tool._duckduckgo_scrape = lambda query: f"FALLBACK:{query}"  # type: ignore[method-assign]
        _assert_equal(serper_tool.run("today"), "SERPER:today", "serper branch")

        fallback_tool = WebSearchTool(serper_api_key=None, allow_fallback=True)
        fallback_tool._serper_search = lambda query: f"SERPER:{query}"  # type: ignore[method-assign]
        fallback_tool._duckduckgo_scrape = lambda query: f"FALLBACK:{query}"  # type: ignore[method-assign]
        _assert_equal(fallback_tool.run("today"), "FALLBACK:today", "fallback branch")

        disabled_tool = WebSearchTool(serper_api_key=None, allow_fallback=False)
        result = disabled_tool.run("today")
        if "Web search unavailable" not in result:
            raise AssertionError(f"disabled branch did not report unavailability: {result}")

        allowed = authorize_network_action("search.serper", SERPER_URL)
        blocked = authorize_network_action("search.fetch", "http://127.0.0.1:8789/private")
        _assert_equal(allowed.allowed, True, "serper policy allowed")
        _assert_equal(blocked.allowed, False, "private search fetch blocked")

        print("PASS: web search mode resolution, branch selection, and policy checks verified.")
        return 0
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        return 1
    finally:
        settings.APP_MODE = original_mode
        settings.SERPER_API_KEY = original_serper
        settings.ALLOW_SERVER_DDG_FALLBACK = original_server_fallback
        settings.configure()


if __name__ == "__main__":
    raise SystemExit(main())
