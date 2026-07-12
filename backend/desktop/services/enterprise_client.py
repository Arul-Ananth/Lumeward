from __future__ import annotations

import requests


class EnterpriseClient:
    """Small synchronous client used by desktop worker threads for server mode."""

    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: str | None = None
        self.user_id: int | None = None
        self.workspace_id: int | None = None

    def _request(self, method: str, path: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.workspace_id is not None:
            headers["X-Workspace-ID"] = str(self.workspace_id)
        response = requests.request(method, f"{self.base_url}{path}", headers=headers, timeout=self.timeout, **kwargs)
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(f"Enterprise server returned {response.status_code}: {detail}")
        return response.json()

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
        payload = self._request("POST", "/news/generate", json={"topic": topic, "context": context})
        return payload.get("content", "")

    def ingest_context(self, text: str, source: str, title: str = "") -> int:
        payload = self._request(
            "POST",
            "/news/ingest/context",
            json={"text": text, "source": source, "title": title},
        )
        return int(payload["chunks_indexed"])
