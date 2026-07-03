from __future__ import annotations

import tempfile
from pathlib import Path

from _bootstrap import setup_project_path

setup_project_path()

from sqlmodel import select

from backend.common.config import AppMode, settings
from backend.common.database import (
    create_db_and_tables,
    get_engine,
    reset_database_runtime,
    session_scope,
)
from backend.common.models.sql import User


def main() -> int:
    original_mode = settings.APP_MODE
    original_data_dir = settings.DATA_DIR
    original_database_url = settings.DATABASE_URL
    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            settings.APP_MODE = AppMode.DESKTOP
            settings.DATA_DIR = Path(temp_dir)
            settings.DATABASE_URL = "postgresql+psycopg://must:be@ignored/desktop"
            reset_database_runtime()
            create_db_and_tables()
            if get_engine().dialect.name != "sqlite":
                print("FAIL: desktop did not ignore the configured PostgreSQL URL.")
                return 1

            try:
                with session_scope() as session:
                    session.add(User(email="rollback@example.com", full_name="Rollback", hashed_password="hash"))
                    session.flush()
                    raise RuntimeError("force rollback")
            except RuntimeError:
                pass

            with session_scope() as session:
                if session.exec(select(User).where(User.email == "rollback@example.com")).first():
                    print("FAIL: failed session was not rolled back.")
                    return 1

        print("PASS: database mode selection, session isolation, and rollback verified.")
        return 0
    finally:
        reset_database_runtime()
        settings.APP_MODE = original_mode
        settings.DATA_DIR = original_data_dir
        settings.DATABASE_URL = original_database_url


if __name__ == "__main__":
    raise SystemExit(main())
