from __future__ import annotations

import uuid

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.common.version import APP_VERSION

DEFAULT_HEADERS = {"User-Agent": f"Lumeward/{APP_VERSION}"}


def build_retry_session(max_retries: int = 2) -> requests.Session:
    retry = Retry(
        total=max_retries,
        read=max_retries,
        connect=max_retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST", "HEAD"),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def build_request_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(DEFAULT_HEADERS)
    headers["X-Request-ID"] = str(uuid.uuid4())
    if extra:
        headers.update({key: value for key, value in extra.items() if value})
    return headers
