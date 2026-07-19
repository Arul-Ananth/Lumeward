from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.common.config import settings
from backend.common.database import (
    check_database_ready,
    create_db_and_tables,
    dispose_database,
    session_scope,
)
from backend.common.version import APP_VERSION
from backend.common.services.memory.vector_db import (
    QdrantUnavailableError,
    check_qdrant_ready,
    close_qdrant,
    initialize_qdrant_collections,
)
from backend.common.services.auth.store import ensure_trusted_lan_user
from backend.common.services.ingestion import cleanup_managed_uploads_on_startup
from backend.server.routers import admin, auth, news
from backend.server.qdrant_runtime import start_bundled_qdrant, stop_bundled_qdrant


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        settings.validate_storage_configuration()
        cleanup_managed_uploads_on_startup()
        create_db_and_tables()
        check_database_ready()
        start_bundled_qdrant()
        check_qdrant_ready()
        initialize_qdrant_collections()
        if settings.is_trusted_lan_auth():
            with session_scope() as session:
                ensure_trusted_lan_user(session)
        yield
    finally:
        try:
            close_qdrant()
        finally:
            try:
                stop_bundled_qdrant()
            finally:
                dispose_database()


def create_app() -> FastAPI:
    app = FastAPI(title="Lumeward Server", version=APP_VERSION, lifespan=lifespan)

    @app.exception_handler(QdrantUnavailableError)
    async def qdrant_unavailable_handler(_: Request, __: QdrantUnavailableError):
        return JSONResponse(
            status_code=503,
            content={"detail": "Memory storage is temporarily unavailable."},
        )

    app.include_router(auth.router, prefix="/auth")
    app.include_router(admin.router, prefix="/admin")
    app.include_router(news.router, prefix="/news")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health/live", tags=["Health"])
    def health_live():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"])
    def health_ready():
        try:
            check_database_ready()
            check_qdrant_ready()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Storage dependency unavailable") from exc
        return {"status": "ready"}

    return app
