from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from _bootstrap import setup_project_path

setup_project_path()

from qdrant_client import QdrantClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def main() -> int:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    qdrant_url = os.getenv("TEST_QDRANT_URL", "").strip()
    if not database_url or not qdrant_url:
        print("SKIP: set TEST_DATABASE_URL and TEST_QDRANT_URL for live server concurrency verification.")
        return 0
    if not database_url.lower().startswith(("postgresql://", "postgresql+psycopg://")):
        print("FAIL: TEST_DATABASE_URL must use PostgreSQL.")
        return 1

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=4,
        max_overflow=2,
        pool_timeout=10,
    )
    qdrant = QdrantClient(
        url=qdrant_url,
        api_key=os.getenv("TEST_QDRANT_API_KEY") or None,
        timeout=10,
    )
    try:
        def database_probe(_: int) -> int:
            with Session(engine) as session:
                return int(session.execute(text("SELECT pg_backend_pid()")).scalar_one())

        def qdrant_probe(_: int) -> int:
            return len(qdrant.get_collections().collections)

        with ThreadPoolExecutor(max_workers=8) as executor:
            database_results = list(executor.map(database_probe, range(40)))
            qdrant_results = list(executor.map(qdrant_probe, range(40)))

        if not database_results or len(set(database_results)) < 2:
            print("FAIL: PostgreSQL concurrency test did not use multiple pooled connections.")
            return 1
        if len(qdrant_results) != 40:
            print("FAIL: Qdrant concurrent readiness probes were incomplete.")
            return 1
        print("PASS: concurrent PostgreSQL sessions and Qdrant requests completed successfully.")
        return 0
    finally:
        qdrant.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
