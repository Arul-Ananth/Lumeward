import sys
import time
from multiprocessing import get_context
from pathlib import Path

root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.append(str(root))

import requests

from backend.desktop.services.api_server import run_api_server


def _wait_for_status(status_queue, timeout: float = 8.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            last = status_queue.get(timeout=0.5)
        except Exception:
            continue
        if last and last.get("status") in {"started", "failed"}:
            return last
    return last


def main() -> int:
    ctx = get_context("spawn")
    ingest_queue = ctx.Queue()
    status_queue = ctx.Queue()
    stop_event = ctx.Event()
    bridge_token = "verify-token"

    process = ctx.Process(
        target=run_api_server,
        args=(ingest_queue, status_queue, stop_event, 12345, bridge_token),
        daemon=True,
    )
    process.start()

    status = _wait_for_status(status_queue)
    if not status or status.get("status") != "started":
        print(f"FAIL: bridge did not start: {status}")
        stop_event.set()
        process.join(timeout=3)
        return 1

    port = status.get("port")
    if not port:
        print("FAIL: bridge started without reporting port.")
        stop_event.set()
        process.join(timeout=3)
        return 1

    url = f"http://127.0.0.1:{port}/ingest"
    denied = requests.post(url, json={"url": "https://example.com", "text": "hello"}, timeout=5)
    if denied.status_code != 403:
        print(f"FAIL: /ingest without token returned {denied.status_code}, expected 403")
        stop_event.set()
        process.join(timeout=3)
        return 1

    options = requests.options(
        url,
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-Bridge-Token",
        },
        timeout=5,
    )
    if options.status_code != 204 or options.headers.get("Access-Control-Allow-Origin") != "http://localhost:5173":
        print(f"FAIL: bridge CORS preflight failed: {options.status_code} {dict(options.headers)}")
        stop_event.set()
        process.join(timeout=3)
        return 1

    resp = requests.post(
        url,
        json={"url": "https://example.com", "text": "hello"},
        headers={"X-Bridge-Token": bridge_token, "Origin": "http://localhost:5173"},
        timeout=5,
    )
    if resp.status_code != 200:
        print(f"FAIL: /ingest returned {resp.status_code}")
        stop_event.set()
        process.join(timeout=3)
        return 1

    try:
        payload = ingest_queue.get(timeout=3)
    except Exception:
        print("FAIL: no payload received in IPC queue.")
        stop_event.set()
        process.join(timeout=3)
        return 1

    if payload.get("url") != "https://example.com":
        print(f"FAIL: unexpected payload {payload}")
        stop_event.set()
        process.join(timeout=3)
        return 1

    stop_event.set()
    process.join(timeout=3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
