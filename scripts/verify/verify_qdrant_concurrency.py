from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from _bootstrap import setup_project_path

setup_project_path()

from backend.common.services.memory import vector_db


class ConcurrentCollectionClient:
    def __init__(self) -> None:
        self.collections: set[str] = set()
        self.lock = threading.Lock()

    def collection_exists(self, name: str) -> bool:
        with self.lock:
            return name in self.collections

    def create_collection(self, *, collection_name: str, vectors_config) -> None:
        with self.lock:
            if collection_name in self.collections:
                raise RuntimeError("already exists")
            self.collections.add(collection_name)


def main() -> int:
    original_client = vector_db._client
    fake_client = ConcurrentCollectionClient()
    vector_db._client = fake_client
    try:
        with ThreadPoolExecutor(max_workers=12) as executor:
            list(executor.map(lambda _: vector_db.ensure_collection("concurrent-test"), range(100)))
        if fake_client.collections != {"concurrent-test"}:
            print("FAIL: concurrent collection initialization was not idempotent.")
            return 1
        print("PASS: concurrent Qdrant collection initialization is idempotent.")
        return 0
    finally:
        vector_db._client = original_client


if __name__ == "__main__":
    raise SystemExit(main())
