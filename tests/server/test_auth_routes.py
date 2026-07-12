from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.common.config import AppMode, AuthMode, settings
from backend.common.database import create_db_and_tables, dispose_database, get_engine, get_session
from backend.server.routers import auth


def test_interactive_signup_login_status_and_logout(isolated_data_dir) -> None:
    dispose_database()
    settings.APP_MODE = AppMode.SERVER
    settings.DATABASE_URL = f"sqlite:///{isolated_data_dir / 'server-auth.db'}"
    settings.TRUSTED_LAN_MODE = False
    settings.AUTH_MODE = AuthMode.INTERACTIVE
    create_db_and_tables()
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")

    def session_override():
        with Session(get_engine()) as session:
            yield session

    app.dependency_overrides[get_session] = session_override

    with TestClient(app) as client:
        signup = client.post(
            "/auth/signup",
            json={"full_name": "Test User", "email": "test@example.com", "password": "secret123"},
        )
        assert signup.status_code == 201
        duplicate = client.post(
            "/auth/signup",
            json={"full_name": "Test User", "email": "test@example.com", "password": "secret123"},
        )
        assert duplicate.status_code == 400

        bad_login = client.post("/auth/login", json={"email": "test@example.com", "password": "wrong"})
        assert bad_login.status_code == 401

        login = client.post("/auth/login", json={"email": "test@example.com", "password": "secret123"})
        assert login.status_code == 200
        payload = login.json()
        assert payload["authenticated"] is True
        assert payload["requires_login"] is True
        assert payload["session_token"]

        status = client.get("/auth/status")
        assert status.status_code == 200
        assert status.json()["authenticated"] is False

        logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {payload['session_token']}"})
        assert logout.status_code == 200
        assert logout.json()["message"] == "Signed out"
