from __future__ import annotations

import asyncio

from _bootstrap import setup_project_path

setup_project_path()

from backend.common.config import AppMode, settings
from backend.common.services.memory import vector_db
from backend.server.app import create_app


class EmptyClient:
    def collection_exists(self, _: str) -> bool:
        return True

    def scroll(self, **_kwargs):
        return [], None


class UnavailableClient(EmptyClient):
    def scroll(self, **_kwargs):
        raise OSError("connection unavailable")


def main() -> int:
    original_mode = settings.APP_MODE
    original_client = vector_db._client
    try:
        settings.APP_MODE = AppMode.SERVER
        vector_db._client = EmptyClient()
        if vector_db.fetch_memories(1) != []:
            print("FAIL: an empty Qdrant collection did not return an empty result.")
            return 1

        vector_db._client = UnavailableClient()
        try:
            vector_db.fetch_memories(1)
        except vector_db.QdrantUnavailableError:
            pass
        else:
            print("FAIL: server mode hid a Qdrant connection failure.")
            return 1

        app = create_app()
        handler = app.exception_handlers[vector_db.QdrantUnavailableError]
        response = asyncio.run(handler(None, vector_db.QdrantUnavailableError("test")))
        if response.status_code != 503:
            print("FAIL: Qdrant failures are not mapped to HTTP 503.")
            return 1

        settings.APP_MODE = AppMode.DESKTOP
        vector_db._client = UnavailableClient()
        if vector_db.fetch_memories(1) != []:
            print("FAIL: desktop mode did not preserve its graceful memory fallback.")
            return 1

        print("PASS: empty Qdrant results and unavailable Qdrant storage are distinguishable.")
        return 0
    finally:
        settings.APP_MODE = original_mode
        vector_db._client = original_client


if __name__ == "__main__":
    raise SystemExit(main())
