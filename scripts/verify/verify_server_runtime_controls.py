from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

from _bootstrap import setup_project_path

setup_project_path()

from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from backend.common.config import AppMode, settings
from backend.main import apply_cli_overrides, start_server
from backend.server import app as server_app
from backend.server.routers import news


def main() -> int:
    if not _verify_readiness_failure():
        return 1
    if not asyncio.run(_verify_ingestion_bound()):
        return 1
    if not _verify_worker_configuration():
        return 1
    print("PASS: readiness failure, ingestion bound, and worker propagation verified.")
    return 0


def _verify_readiness_failure() -> bool:
    app = server_app.create_app()
    with patch.object(server_app, "check_database_ready", side_effect=RuntimeError("offline")):
        response = TestClient(app).get("/health/ready")
    if response.status_code != 503:
        print("FAIL: readiness did not return 503 when storage was unavailable.")
        return False
    return True


async def _verify_ingestion_bound() -> bool:
    active = 0
    peak = 0
    lock = threading.Lock()

    def fake_ingestion(*args):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return object()

    original_semaphore = news.ingestion_semaphore
    news.ingestion_semaphore = asyncio.Semaphore(2)
    try:
        with patch.object(news, "_ingest_folder_in_worker", side_effect=fake_ingestion):
            await asyncio.gather(
                *(
                    news._run_bounded_ingestion(
                        UploadFile(io.BytesIO(b"zip"), filename="folder.zip", size=3),
                        "folder.zip",
                        index,
                    )
                    for index in range(10)
                )
            )
    finally:
        news.ingestion_semaphore = original_semaphore
    if peak != 2:
        print(f"FAIL: ingestion concurrency peak was {peak}, expected 2.")
        return False
    return True


def _verify_worker_configuration() -> bool:
    fields = {
        "APP_MODE": settings.APP_MODE,
        "DATABASE_URL": settings.DATABASE_URL,
        "QDRANT_URL": settings.QDRANT_URL,
        "SERVER_WORKERS": settings.SERVER_WORKERS,
        "ENGINE_ENABLED": settings.ENGINE_ENABLED,
    }
    original_app_mode_env = os.environ.get("APP_MODE")
    calls: list[dict] = []
    fake_uvicorn = SimpleNamespace(run=lambda **kwargs: calls.append(kwargs))
    try:
        settings.DATABASE_URL = "postgresql+psycopg://user:password@localhost/lumeward"
        settings.QDRANT_URL = "http://127.0.0.1:6333"
        settings.SERVER_WORKERS = 3
        settings.ENGINE_ENABLED = False
        args = argparse.Namespace(
            mode="server",
            auth_mode=None,
            host=None,
            port=None,
            reload=False,
        )
        apply_cli_overrides(args)
        with patch.dict(sys.modules, {"uvicorn": fake_uvicorn}):
            start_server()
        if os.environ.get("APP_MODE") != "SERVER" or not calls or calls[0].get("workers") != 3:
            print("FAIL: selected mode or worker count was not propagated.")
            return False
        return True
    finally:
        for key, value in fields.items():
            setattr(settings, key, value)
        if original_app_mode_env is None:
            os.environ.pop("APP_MODE", None)
        else:
            os.environ["APP_MODE"] = original_app_mode_env


if __name__ == "__main__":
    raise SystemExit(main())
