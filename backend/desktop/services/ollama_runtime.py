from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import requests

from backend.common.services.network import build_request_headers


@dataclass(frozen=True)
class OllamaCheckResult:
    ok: bool
    message: str


def ollama_tags_url(base_url: str) -> str:
    parsed = urlparse((base_url or "http://localhost:11434").strip())
    if not parsed.scheme:
        parsed = urlparse(f"http://{base_url.strip()}")
    if parsed.path.rstrip("/") in {"", "/v1"}:
        path = "/api/tags"
    else:
        path = f"{parsed.path.rstrip('/')}/api/tags"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def ping_ollama(base_url: str, *, timeout_seconds: float = 3.0) -> OllamaCheckResult:
    target = ollama_tags_url(base_url)
    try:
        response = requests.get(target, headers=build_request_headers(), timeout=timeout_seconds)
        response.raise_for_status()
    except Exception as exc:
        return OllamaCheckResult(False, f"Ollama did not respond at {target}: {exc}")
    return OllamaCheckResult(True, f"Ollama is reachable at {target}.")


def start_ollama() -> OllamaCheckResult:
    executable = shutil.which("ollama")
    if not executable:
        return OllamaCheckResult(False, "The `ollama` command was not found on PATH.")

    creation_flags = 0
    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        subprocess.Popen(
            [executable, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
    except Exception as exc:
        return OllamaCheckResult(False, f"Could not start Ollama: {exc}")
    return OllamaCheckResult(True, "Ollama start command was launched.")
