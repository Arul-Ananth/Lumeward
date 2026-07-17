from __future__ import annotations

from urllib.parse import urlparse

import requests

from backend.common.config import settings


class EnterpriseClient:
    """Small synchronous client used by desktop worker threads for server mode."""

    def __init__(
        self,
        base_url: str,
        timeout: float | None = None,
        generation_timeout: float | None = None,
    ) -> None:
        self.base_url = base_url.strip().rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Enterprise Server URL must be an absolute http:// or https:// URL.")
        self.timeout = float(
            settings.ENTERPRISE_REQUEST_TIMEOUT_SECONDS if timeout is None else timeout
        )
        self.generation_timeout = float(
            settings.ENTERPRISE_GENERATION_TIMEOUT_SECONDS
            if generation_timeout is None
            else generation_timeout
        )
        if self.timeout <= 0 or self.generation_timeout <= 0:
            raise ValueError("Enterprise request timeouts must be positive.")
        self.token: str | None = None
        self.user_id: int | None = None
        self.workspace_id: int | None = None

    def _request(self, method: str, path: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        request_timeout = kwargs.pop("timeout", self.timeout)
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.workspace_id is not None:
            headers["X-Workspace-ID"] = str(self.workspace_id)
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=request_timeout,
                **kwargs,
            )
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Enterprise request timed out while calling {path}.") from exc
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            hint = ""
            if response.status_code == 404:
                hint = (
                    " Check that Server URL points to the Lumeward backend "
                    "(for local development, http://127.0.0.1:8000), not the web UI on port 5173."
                )
            raise RuntimeError(f"Enterprise server returned {response.status_code}: {detail}.{hint}")
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise RuntimeError(
                "The configured Enterprise Server URL does not appear to be a Lumeward backend. "
                "For local development use http://127.0.0.1:8000, not the web UI on port 5173."
            ) from exc

    def check_server(self) -> None:
        payload = self._request("GET", "/health/live")
        if payload.get("status") != "ok":
            raise RuntimeError("Enterprise server health check returned an unexpected response.")

    def login(self, email: str, password: str) -> None:
        payload = self._request("POST", "/auth/login", json={"email": email, "password": password})
        self.token = payload.get("session_token")
        self.user_id = payload.get("user_id")
        if not self.token or not self.user_id:
            raise RuntimeError("Server login did not return a session token.")

    def signup(self, full_name: str, email: str, password: str) -> None:
        self._request(
            "POST",
            "/auth/signup",
            json={"full_name": full_name, "email": email, "password": password},
        )

    def list_workspaces(self) -> list[dict]:
        return self._request("GET", "/auth/workspaces")

    def generate(self, topic: str, context: str = "") -> str:
        payload = self._request(
            "POST",
            "/news/generate",
            json={"topic": topic, "context": context},
            timeout=(self.timeout, self.generation_timeout),
        )
        return payload.get("content", "")

    def ingest_context(self, text: str, source: str, title: str = "") -> int:
        payload = self._request(
            "POST",
            "/news/ingest/context",
            json={"text": text, "source": source, "title": title},
        )
        return int(payload["chunks_indexed"])
