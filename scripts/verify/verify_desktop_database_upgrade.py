from __future__ import annotations

import tempfile
from pathlib import Path

from _bootstrap import setup_project_path

setup_project_path()

from sqlalchemy import text

from backend.common.config import AppMode, settings
from backend.common.database import create_db_and_tables, get_engine, reset_database_runtime


def main() -> int:
    original_mode = settings.APP_MODE
    original_data_dir = settings.DATA_DIR
    original_database_url = settings.DATABASE_URL
    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            settings.APP_MODE = AppMode.DESKTOP
            settings.DATA_DIR = Path(temp_dir)
            settings.DATABASE_URL = "postgresql+psycopg://ignored:ignored@ignored/ignored"
            reset_database_runtime()
            engine = get_engine()

            with engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE user ("
                    "id INTEGER PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, "
                    "full_name VARCHAR(100) NOT NULL, hashed_password VARCHAR NOT NULL)"
                )
                connection.exec_driver_sql(
                    "INSERT INTO user (id, email, full_name, hashed_password) "
                    "VALUES (1, 'existing@example.com', 'Existing User', 'hash')"
                )
                connection.exec_driver_sql(
                    "CREATE TABLE derivedmemory ("
                    "id INTEGER PRIMARY KEY, memory_type VARCHAR(64) NOT NULL, "
                    "ts DATETIME NOT NULL, source_refs TEXT NOT NULL, "
                    "summary_text TEXT NOT NULL, qdrant_point_id VARCHAR(64) NOT NULL)"
                )
                connection.exec_driver_sql(
                    "INSERT INTO derivedmemory "
                    "(id, memory_type, ts, source_refs, summary_text, qdrant_point_id) "
                    "VALUES (1, 'legacy', CURRENT_TIMESTAMP, '{}', 'preserve me', 'point-1')"
                )

            create_db_and_tables()

            with engine.connect() as connection:
                columns = {
                    row[1] for row in connection.exec_driver_sql("PRAGMA table_info('derivedmemory')").fetchall()
                }
                preserved = connection.execute(
                    text("SELECT summary_text, user_id FROM derivedmemory WHERE id = 1")
                ).one()
                migration_count = connection.execute(text("SELECT COUNT(*) FROM schemamigration")).scalar_one()
                identity_count = connection.execute(text("SELECT COUNT(*) FROM authidentity")).scalar_one()

            if "user_id" not in columns or preserved != ("preserve me", -1):
                print("FAIL: legacy desktop data was not upgraded and preserved.")
                return 1
            if migration_count != 4 or identity_count != 1:
                print("FAIL: desktop migrations were not recorded or identity backfill failed.")
                return 1
        print("PASS: existing desktop SQLite schema upgraded without data loss.")
        return 0
    finally:
        reset_database_runtime()
        settings.APP_MODE = original_mode
        settings.DATA_DIR = original_data_dir
        settings.DATABASE_URL = original_database_url


if __name__ == "__main__":
    raise SystemExit(main())
