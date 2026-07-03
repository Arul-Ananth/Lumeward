from __future__ import annotations

import tempfile
from pathlib import Path

from _bootstrap import setup_project_path

setup_project_path()

from sqlmodel import select

from backend.common.config import AppMode, settings
from backend.common.database import (
    check_server_schema_ready,
    reset_database_runtime,
    session_scope,
)
from backend.common.models.sql import ApplicationSchema, User
from scripts.dev import database


def main() -> int:
    original = {
        "APP_MODE": settings.APP_MODE,
        "DATABASE_URL": settings.DATABASE_URL,
        "QDRANT_URL": settings.QDRANT_URL,
    }
    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            database_path = Path(temp_dir) / "server-test.db"
            settings.APP_MODE = AppMode.SERVER
            settings.DATABASE_URL = f"sqlite:///{database_path.as_posix()}"
            settings.QDRANT_URL = "http://127.0.0.1:6333"
            reset_database_runtime()

            database.initialize()
            check_server_schema_ready()
            with session_scope() as session:
                session.add(User(email="remove@example.com", full_name="Remove", hashed_password="hash"))
                session.commit()

            database.refresh(include_qdrant=False)
            check_server_schema_ready()
            with session_scope() as session:
                if session.exec(select(User)).first() is not None:
                    print("FAIL: relational refresh did not remove existing data.")
                    return 1
                state = session.get(ApplicationSchema, 1)
                if state is None or state.version != database.SERVER_SCHEMA_VERSION:
                    print("FAIL: refreshed schema version was not recorded.")
                    return 1

            try:
                database.initialize()
            except RuntimeError:
                pass
            else:
                print("FAIL: initialize accepted an existing application schema.")
                return 1

        print("PASS: explicit initialize, version validation, and destructive refresh verified.")
        return 0
    finally:
        reset_database_runtime()
        for field, value in original.items():
            setattr(settings, field, value)


if __name__ == "__main__":
    raise SystemExit(main())
