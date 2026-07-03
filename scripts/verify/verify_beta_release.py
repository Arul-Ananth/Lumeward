from __future__ import annotations

import warnings

from _bootstrap import setup_project_path, use_temp_data_dir

setup_project_path()
tmp = use_temp_data_dir()

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
    category=Warning,
)

from fastapi.testclient import TestClient

from backend.common.config import AppMode, settings
from backend.common.services.memory import vector_db
from backend.common.version import APP_VERSION
from backend.server.app import create_app


def main() -> int:
    try:
        settings.APP_MODE = AppMode.DESKTOP
        app = create_app()
        if app.version != APP_VERSION or APP_VERSION != "1.0.0-beta.1":
            print(f"FAIL: unexpected app version {app.version!r} / {APP_VERSION!r}")
            return 1

        settings.TRUSTED_LAN_MODE = True
        settings.AUTH_MODE = None
        with TestClient(app) as client:
            if client.get("/health/live").status_code != 200:
                print("FAIL: liveness endpoint is unavailable")
                return 1
            if client.get("/health/ready").status_code != 200:
                print("FAIL: readiness endpoint is unavailable with healthy local test storage")
                return 1
            response = client.get("/news/sources")
            if response.status_code != 200:
                print(f"FAIL: /news/sources returned {response.status_code}")
                return 1
            sources = response.json()
            if not sources:
                print("FAIL: /news/sources returned no planned sources")
                return 1
            if any(item.get("implemented") for item in sources):
                print("FAIL: beta source metadata marked a source as implemented")
                return 1
            required = {"telegram", "whatsapp_export", "rss", "email"}
            actual = {item.get("key") for item in sources}
            missing = required - actual
            if missing:
                print(f"FAIL: missing source metadata keys: {sorted(missing)}")
                return 1

        print("PASS: beta version and source metadata endpoint verified.")
        return 0
    finally:
        vector_db.close_qdrant()
        tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
