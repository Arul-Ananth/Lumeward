from __future__ import annotations

import tempfile
from pathlib import Path

from _bootstrap import setup_project_path

setup_project_path()

from backend.common.config import AppMode, settings
from backend.common.database import get_engine, reset_database_runtime
from backend.common.services.memory import vector_db


def main() -> int:
    original = {
        "APP_MODE": settings.APP_MODE,
        "DATA_DIR": settings.DATA_DIR,
        "DATABASE_URL": settings.DATABASE_URL,
        "QDRANT_URL": settings.QDRANT_URL,
        "SERVER_WORKERS": settings.SERVER_WORKERS,
        "DB_POOL_SIZE": settings.DB_POOL_SIZE,
        "DB_MAX_OVERFLOW": settings.DB_MAX_OVERFLOW,
        "DB_POOL_TIMEOUT_SECONDS": settings.DB_POOL_TIMEOUT_SECONDS,
        "DB_POOL_RECYCLE_SECONDS": settings.DB_POOL_RECYCLE_SECONDS,
        "QDRANT_TIMEOUT_SECONDS": settings.QDRANT_TIMEOUT_SECONDS,
        "INGESTION_CONCURRENCY": settings.INGESTION_CONCURRENCY,
    }
    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            settings.APP_MODE = AppMode.DESKTOP
            settings.DATA_DIR = Path(temp_dir)
            settings.DATABASE_URL = ""
            settings.QDRANT_URL = ""
            reset_database_runtime()
            vector_db.close_qdrant()

            if get_engine().dialect.name != "sqlite":
                print("FAIL: desktop mode did not select SQLite.")
                return 1
            if not getattr(vector_db.get_client(), "_client", None) and not (Path(temp_dir) / "qdrant_db").exists():
                print("FAIL: desktop mode did not initialize embedded Qdrant.")
                return 1

        settings.APP_MODE = AppMode.SERVER
        settings.DATABASE_URL = ""
        settings.QDRANT_URL = ""
        try:
            settings.validate_storage_configuration()
        except RuntimeError:
            pass
        else:
            print("FAIL: server mode accepted missing PostgreSQL and Qdrant configuration.")
            return 1

        settings.DATABASE_URL = "sqlite:///server-must-not-use-this.db"
        settings.QDRANT_URL = "http://qdrant.invalid:6333"
        try:
            settings.validate_storage_configuration()
        except RuntimeError:
            pass
        else:
            print("FAIL: server mode accepted SQLite.")
            return 1

        settings.DATABASE_URL = "postgresql+psycopg://user:password@postgres.invalid/lumeward"
        settings.QDRANT_URL = "https://qdrant.invalid:6333"
        settings.validate_storage_configuration()

        invalid_values = (
            ("SERVER_WORKERS", 0),
            ("DB_POOL_SIZE", 0),
            ("DB_MAX_OVERFLOW", -1),
            ("DB_POOL_TIMEOUT_SECONDS", 0),
            ("DB_POOL_RECYCLE_SECONDS", 0),
            ("QDRANT_TIMEOUT_SECONDS", 0),
            ("INGESTION_CONCURRENCY", 0),
        )
        for field, invalid_value in invalid_values:
            original_value = getattr(settings, field)
            setattr(settings, field, invalid_value)
            try:
                settings.validate_storage_configuration()
            except RuntimeError:
                pass
            else:
                print(f"FAIL: server mode accepted invalid {field}.")
                return 1
            finally:
                setattr(settings, field, original_value)

        settings.QDRANT_URL = "qdrant.invalid:6333"
        try:
            settings.validate_storage_configuration()
        except RuntimeError:
            pass
        else:
            print("FAIL: server mode accepted a non-absolute Qdrant URL.")
            return 1
        print("PASS: desktop local storage and strict server storage selection verified.")
        return 0
    finally:
        vector_db.close_qdrant()
        reset_database_runtime()
        for key, value in original.items():
            setattr(settings, key, value)


if __name__ == "__main__":
    raise SystemExit(main())
