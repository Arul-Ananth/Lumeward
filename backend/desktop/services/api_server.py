from __future__ import annotations

import logging
import socket
import threading
import time
from multiprocessing import Queue

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel

from backend.common.config import settings

logger = logging.getLogger(__name__)

BRIDGE_TOKEN_HEADER = "X-Bridge-Token"
BRIDGE_ALLOWED_METHODS = "POST, OPTIONS"
BRIDGE_ALLOWED_HEADERS = f"Content-Type, {BRIDGE_TOKEN_HEADER}"

app = FastAPI()
_ingest_queue: Queue | None = None
_bridge_token: str | None = None


def _allowed_origins() -> set[str]:
    return set(settings.cors_origins()) | {"http://127.0.0.1:5173", "http://localhost:5173"}


def _cors_origin(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin in _allowed_origins():
        return origin
    return None


def _with_cors_headers(response: Response, request: Request) -> Response:
    origin = _cors_origin(request)
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = BRIDGE_ALLOWED_METHODS
        response.headers["Access-Control-Allow-Headers"] = BRIDGE_ALLOWED_HEADERS
    return response


@app.middleware("http")
async def add_bridge_cors_headers(request: Request, call_next):
    response = await call_next(request)
    return _with_cors_headers(response, request)


class IngestPayload(BaseModel):
    url: str | None = None
    text: str | None = None


@app.options("/ingest")
def ingest_options(request: Request):
    return _with_cors_headers(Response(status_code=204), request)


def init_queue(queue: Queue, bridge_token: str) -> None:
    global _ingest_queue, _bridge_token
    _ingest_queue = queue
    _bridge_token = bridge_token


@app.post("/ingest")
def ingest(
    payload: IngestPayload,
    bridge_token: str | None = Header(default=None, alias=BRIDGE_TOKEN_HEADER),
):
    if bridge_token != _bridge_token:
        raise HTTPException(status_code=403, detail="invalid bridge token")
    if not payload.url and not payload.text:
        raise HTTPException(status_code=400, detail="url or text required")
    if _ingest_queue is None:
        raise HTTPException(status_code=503, detail="queue not ready")
    _ingest_queue.put(payload.model_dump())
    return {"status": "ok"}


def _reserve_port(host: str, port: int) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    actual_port = sock.getsockname()[1]
    sock.close()
    return actual_port


def _wait_for_server(
    host: str,
    port: int,
    server_thread: threading.Thread,
    stop_event,
    timeout: float = 5.0,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stop_event.is_set():
            return False
        if not server_thread.is_alive():
            return False
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def run_api_server(
    ingest_queue: Queue,
    status_queue: Queue | None,
    stop_event,
    preferred_port: int = 12345,
    bridge_token: str = "",
) -> None:
    init_queue(ingest_queue, bridge_token)
    host = "127.0.0.1"
    errors: list[str] = []

    for candidate in (preferred_port, 0):
        try:
            port = _reserve_port(host, candidate)
        except OSError as exc:
            errors.append(f"bind failed on port {candidate}: {exc}")
            continue

        try:
            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="info",
                lifespan="off",
                log_config=None,
            )
            server = uvicorn.Server(config)
        except Exception as exc:
            errors.append(f"uvicorn init failed on port {port}: {exc}")
            continue

        def _watch_stop() -> None:
            stop_event.wait()
            server.should_exit = True

        watcher = threading.Thread(target=_watch_stop, daemon=True)
        watcher.start()

        server_thread = threading.Thread(target=server.run, daemon=False)
        server_thread.start()

        if status_queue is not None:
            status_queue.put({"status": "starting", "port": port})

        if not _wait_for_server(host, port, server_thread, stop_event):
            if status_queue is not None:
                status_queue.put({"status": "failed", "error": "Bridge failed to start."})
            server.should_exit = True
            server_thread.join(timeout=2)
            return

        if status_queue is not None:
            status_queue.put({"status": "started", "port": port})

        server_thread.join()
        return

    if status_queue is not None:
        detail = "; ".join(errors) if errors else "unknown error"
        status_queue.put({"status": "failed", "error": detail})
