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


def test_two_user_organization_and_workspace_flow(isolated_data_dir) -> None:
    dispose_database()
    settings.APP_MODE = AppMode.SERVER
    settings.DATABASE_URL = f"sqlite:///{isolated_data_dir / 'enterprise-auth.db'}"
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
        for name, email in (("Admin", "admin@example.com"), ("Member", "member@example.com")):
            assert client.post(
                "/auth/signup", json={"full_name": name, "email": email, "password": "secret123"}
            ).status_code == 201
        admin_login = client.post(
            "/auth/login", json={"email": "admin@example.com", "password": "secret123"}
        ).json()
        member_login = client.post(
            "/auth/login", json={"email": "member@example.com", "password": "secret123"}
        ).json()
        admin_headers = {"Authorization": f"Bearer {admin_login['session_token']}"}
        member_headers = {"Authorization": f"Bearer {member_login['session_token']}"}
        organization = client.post(
            "/auth/organizations", headers=admin_headers, json={"name": "Acme", "slug": "acme"}
        ).json()
        workspace = client.post(
            "/auth/workspaces", headers=admin_headers,
            json={"organization_id": organization["id"], "name": "Engineering", "slug": "engineering"},
        ).json()

        blocked = client.post(
            f"/auth/workspaces/{workspace['id']}/members", headers=admin_headers,
            json={"email": "member@example.com", "role": "member"},
        )
        assert blocked.status_code == 400
        assert client.post(
            f"/auth/organizations/{organization['id']}/members", headers=admin_headers,
            json={"email": "member@example.com", "role": "member"},
        ).status_code == 201
        assert client.post(
            f"/auth/workspaces/{workspace['id']}/members", headers=admin_headers,
            json={"email": "member@example.com", "role": "member"},
        ).status_code == 201
        assert client.get("/auth/workspaces", headers=member_headers).json()[0]["id"] == workspace["id"]
        assert client.post(
            f"/auth/organizations/{organization['id']}/members", headers=member_headers,
            json={"email": "admin@example.com", "role": "member"},
        ).status_code == 403
        assert client.post(
            f"/auth/workspaces/{workspace['id']}/members", headers=admin_headers,
            json={"email": "member@example.com", "role": "owner"},
        ).status_code == 422
