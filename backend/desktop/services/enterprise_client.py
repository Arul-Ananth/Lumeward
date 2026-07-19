from __future__ import annotations

import requests


class EnterpriseClient:
    """Small synchronous client used by desktop worker threads for server mode."""

    def __init__(
        self,
        base_url: str,
        *,
        connect_timeout: float = 5.0,
        request_timeout: float = 30.0,
        generation_timeout: float = 300.0,
    ) -> None:
        for name, value in (
            ("connect_timeout", connect_timeout),
            ("request_timeout", request_timeout),
            ("generation_timeout", generation_timeout),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive.")
        self.base_url = base_url.rstrip("/")
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout
        self.generation_timeout = generation_timeout
        self.token: str | None = None
        self.user_id: int | None = None
        self.workspace_id: int | None = None

    def _request(
        self,
        method: str,
        path: str,
        *,
        read_timeout: float | None = None,
        **kwargs,
    ):
        headers = dict(kwargs.pop("headers", {}) or {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.workspace_id is not None:
            headers["X-Workspace-ID"] = str(self.workspace_id)
        effective_read_timeout = (
            read_timeout if read_timeout is not None else self.request_timeout
        )
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=(self.connect_timeout, effective_read_timeout),
                **kwargs,
            )
        except requests.ConnectTimeout as exc:
            raise RuntimeError(
                f"Could not connect to the enterprise server within {self.connect_timeout:g} seconds."
            ) from exc
        except requests.ReadTimeout as exc:
            raise RuntimeError(
                f"Enterprise request {path} did not complete within {effective_read_timeout:g} seconds."
            ) from exc
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
        payload = self._request(
            "POST",
            "/news/generate",
            read_timeout=self.generation_timeout,
            json={"topic": topic, "context": context},
        )
        return payload.get("content", "")

    def ingest_context(self, text: str, source: str, title: str = "") -> int:
        payload = self._request(
            "POST",
            "/news/ingest/context",
            json={"text": text, "source": source, "title": title},
        )
        return int(payload["chunks_indexed"])
