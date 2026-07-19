from __future__ import annotations

from typing import Any

import pytest
import requests

from backend.desktop.services.enterprise_client import EnterpriseClient


class StubResponse:
    ok = True

    def json(self) -> dict[str, Any]:
        return {"content": "Generated briefing", "memories": []}


def test_generation_uses_long_read_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, Any] = {}

    def request(method: str, url: str, **kwargs: Any) -> StubResponse:
        observed.update(method=method, url=url, **kwargs)
        return StubResponse()

    monkeypatch.setattr(requests, "request", request)
    client = EnterpriseClient(
        "http://127.0.0.1:8000/",
        connect_timeout=4,
        request_timeout=20,
        generation_timeout=240,
    )

    assert client.generate("technology") == "Generated briefing"
    assert observed["timeout"] == (4, 240)
    assert observed["url"] == "http://127.0.0.1:8000/news/generate"


def test_regular_request_uses_shorter_read_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, Any] = {}

    def request(method: str, url: str, **kwargs: Any) -> StubResponse:
        observed.update(method=method, url=url, **kwargs)
        return StubResponse()

    monkeypatch.setattr(requests, "request", request)
    client = EnterpriseClient("http://server", connect_timeout=3, request_timeout=25)

    client.list_workspaces()
    assert observed["timeout"] == (3, 25)


def test_timeout_error_names_operation_and_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    def request(*args: Any, **kwargs: Any) -> StubResponse:
        raise requests.ReadTimeout("timed out")

    monkeypatch.setattr(requests, "request", request)
    client = EnterpriseClient("http://server", generation_timeout=180)

    with pytest.raises(RuntimeError, match=r"/news/generate.*180 seconds"):
        client.generate("technology")


def test_connect_timeout_has_distinct_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def request(*args: Any, **kwargs: Any) -> StubResponse:
        raise requests.ConnectTimeout("timed out")

    monkeypatch.setattr(requests, "request", request)
    client = EnterpriseClient("http://server", connect_timeout=7)

    with pytest.raises(RuntimeError, match="connect.*7 seconds"):
        client.generate("technology")


@pytest.mark.parametrize("name", ["connect_timeout", "request_timeout", "generation_timeout"])
def test_timeout_values_must_be_positive(name: str) -> None:
    with pytest.raises(ValueError, match=f"{name} must be positive"):
        EnterpriseClient("http://server", **{name: 0})
