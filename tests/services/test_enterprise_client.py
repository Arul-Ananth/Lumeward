from __future__ import annotations

from typing import Any
from unittest.mock import Mock

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


def test_enterprise_client_rejects_non_absolute_url() -> None:
    with pytest.raises(ValueError, match="absolute"):
        EnterpriseClient("127.0.0.1:8000")


def test_health_check_explains_frontend_url(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock(ok=True)
    response.json.side_effect = requests.exceptions.JSONDecodeError("bad json", "<html>", 0)
    monkeypatch.setattr(requests, "request", Mock(return_value=response))

    client = EnterpriseClient("http://127.0.0.1:5173")

    with pytest.raises(RuntimeError, match="port 5173"):
        client.check_server()


def test_404_explains_backend_url(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock(ok=False, status_code=404, text="Not Found")
    response.json.return_value = {"detail": "Not Found"}
    monkeypatch.setattr(requests, "request", Mock(return_value=response))

    client = EnterpriseClient("http://127.0.0.1:5173")

    with pytest.raises(RuntimeError, match="http://127.0.0.1:8000"):
        client.login("user@example.com", "password")


def test_enterprise_startup_failure_falls_back_to_local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.desktop import main as desktop_main

    class UnavailableClient:
        def __init__(self, _server_url: str) -> None:
            pass

        def check_server(self) -> None:
            raise RuntimeError("not a backend")

    critical = Mock()
    monkeypatch.setattr(desktop_main, "EnterpriseClient", UnavailableClient)
    monkeypatch.setattr(desktop_main.QMessageBox, "critical", critical)

    client, user_id = desktop_main.prompt_for_enterprise_connection(
        "http://127.0.0.1:5173", 42,
    )

    assert client is None
    assert user_id == 42
    assert "continue in local mode" in critical.call_args.args[2]


@pytest.mark.parametrize("name", ["connect_timeout", "request_timeout", "generation_timeout"])
def test_timeout_values_must_be_positive(name: str) -> None:
    with pytest.raises(ValueError, match=f"{name} must be positive"):
        EnterpriseClient("http://server", **{name: 0})
