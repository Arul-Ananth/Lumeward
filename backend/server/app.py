from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from backend.common.config import settings
from backend.common.database import create_db_and_tables, engine
from backend.common.version import APP_VERSION
from backend.common.services.auth.store import ensure_trusted_lan_user
from backend.common.services.ingestion import cleanup_managed_uploads_on_startup
from backend.server.routers import auth, news


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_managed_uploads_on_startup()
    create_db_and_tables()
    if settings.is_trusted_lan_auth():
        with Session(engine) as session:
            ensure_trusted_lan_user(session)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Lumeward Server", version=APP_VERSION, lifespan=lifespan)
    app.include_router(auth.router, prefix="/auth")
    app.include_router(news.router, prefix="/news")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app
