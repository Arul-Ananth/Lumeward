from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from backend.desktop.services.enterprise_client import EnterpriseClient


def test_enterprise_client_rejects_non_absolute_url() -> None:
    with pytest.raises(ValueError, match="absolute"):
        EnterpriseClient("127.0.0.1:8000")


def test_health_check_explains_frontend_url(monkeypatch) -> None:
    response = Mock(ok=True)
    response.json.side_effect = requests.exceptions.JSONDecodeError("bad json", "<html>", 0)
    monkeypatch.setattr(requests, "request", Mock(return_value=response))

    client = EnterpriseClient("http://127.0.0.1:5173")

    with pytest.raises(RuntimeError, match="port 5173"):
        client.check_server()


def test_404_explains_backend_url(monkeypatch) -> None:
    response = Mock(ok=False, status_code=404, text="Not Found")
    response.json.return_value = {"detail": "Not Found"}
    monkeypatch.setattr(requests, "request", Mock(return_value=response))

    client = EnterpriseClient("http://127.0.0.1:5173")

    with pytest.raises(RuntimeError, match="http://127.0.0.1:8000"):
        client.login("user@example.com", "password")


def test_enterprise_startup_failure_falls_back_to_local_mode(monkeypatch) -> None:
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


def test_generation_uses_long_read_timeout(monkeypatch) -> None:
    response = Mock(ok=True)
    response.json.return_value = {"content": "Generated briefing"}
    request = Mock(return_value=response)
    monkeypatch.setattr(requests, "request", request)

    client = EnterpriseClient("http://127.0.0.1:8000")

    assert client.generate("tech hiring") == "Generated briefing"
    assert request.call_args.kwargs["timeout"] == (15.0, 600.0)


def test_enterprise_timeout_can_be_overridden() -> None:
    client = EnterpriseClient(
        "http://127.0.0.1:8000",
        timeout=7,
        generation_timeout=90,
    )

    assert client.timeout == 7.0
    assert client.generation_timeout == 90.0
