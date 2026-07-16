from __future__ import annotations

from urllib.parse import urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from backend.common.config import AppMode, AuthMode, settings
from backend.common.database import create_db_and_tables, dispose_database, get_engine, get_session
from backend.common.models.sql import (
    AuthSession,
    Organization,
    OrganizationAuditEvent,
    OrganizationInvitation,
    OrganizationMembership,
    User,
    Workspace,
    WorkspaceMembership,
)
from backend.common.services.auth.store import hash_session_token
from backend.common.services.invitation_mail import MailDeliveryResult
from backend.common.services import organization_admin
from backend.server.routers import admin, auth, news


@pytest.fixture
def admin_client(isolated_data_dir) -> TestClient:
    dispose_database()
    settings.APP_MODE = AppMode.SERVER
    settings.DATABASE_URL = f"sqlite:///{isolated_data_dir / 'admin-portal.db'}"
    settings.TRUSTED_LAN_MODE = False
    settings.AUTH_MODE = AuthMode.INTERACTIVE
    create_db_and_tables()

    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")
    app.include_router(admin.router, prefix="/admin")
    app.include_router(news.router, prefix="/news")

    def session_override():
        with Session(get_engine()) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        yield client


def _signup_organization(
    client: TestClient,
    *,
    email: str = "owner@example.com",
    organization_name: str = "Acme Research",
) -> dict:
    response = client.post(
        "/auth/organization-signup",
        json={
            "full_name": "Organization Owner",
            "email": email,
            "password": "secret123",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["organization_role"] == "organization_admin"
    assert payload["onboarding_required"] is True
    assert payload["session_token"]
    return payload


def _headers(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['session_token']}"}


def _invite_token(invite_url: str) -> str:
    return urlparse(invite_url).path.rstrip("/").rsplit("/", 1)[-1]


def test_organization_signup_is_atomic_and_generates_unique_slugs(admin_client: TestClient) -> None:
    first = _signup_organization(admin_client)
    assert first["organization"]["slug"] == "acme-research"

    duplicate = admin_client.post(
        "/auth/organization-signup",
        json={
            "full_name": "Duplicate",
            "email": "owner@example.com",
            "password": "secret123",
            "organization_name": "Should Roll Back",
        },
    )
    assert duplicate.status_code == 409

    second = _signup_organization(
        admin_client,
        email="second-owner@example.com",
        organization_name="Acme Research",
    )
    assert second["organization"]["slug"] == "acme-research-2"

    with Session(get_engine()) as session:
        assert session.exec(select(func.count(User.id))).one() == 2
        assert session.exec(select(func.count(Organization.id))).one() == 2
        assert session.exec(select(func.count(OrganizationMembership.id))).one() == 2
        assert session.exec(select(func.count(AuthSession.id))).one() == 2
        assert session.exec(
            select(Organization).where(Organization.name == "Should Roll Back")
        ).first() is None
        events = session.exec(select(OrganizationAuditEvent)).all()
        assert len(events) == 2
        assert all(event.action == "organization.created" for event in events)


def test_signup_keeps_legacy_user_only_route_compatible(admin_client: TestClient) -> None:
    legacy = admin_client.post(
        "/auth/signup",
        json={"full_name": "Desktop User", "email": "desktop@example.com", "password": "secret123"},
    )
    assert legacy.status_code == 201
    assert legacy.json()["auth_provider"] == "interactive_password"


def test_bootstrap_requires_auth_and_workspace_completes_onboarding(admin_client: TestClient) -> None:
    assert admin_client.get("/admin/bootstrap").status_code == 401
    owner = _signup_organization(admin_client)
    headers = _headers(owner)

    initial = admin_client.get("/admin/bootstrap", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["workspaces"] == []
    assert initial.json()["onboarding_required"] is True

    created = admin_client.post("/admin/workspaces", headers=headers, json={"name": "Engineering"})
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "workspace_admin"
    assert created.json()["slug"] == "engineering"
    assert created.json()["admin_count"] == 1

    bootstrap = admin_client.get("/admin/bootstrap", headers=headers).json()
    assert bootstrap["onboarding_required"] is False
    assert [workspace["name"] for workspace in bootstrap["workspaces"]] == ["Engineering"]
    assert bootstrap["workspaces"][0]["admin_count"] == 1


def test_ordinary_member_cannot_share_workspace_context_but_admin_route_is_audited(
    admin_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _signup_organization(admin_client)
    owner_headers = _headers(owner)
    workspace = admin_client.post(
        "/admin/workspaces", headers=owner_headers, json={"name": "Research"}
    ).json()
    invitation = admin_client.post(
        "/admin/invitations",
        headers=owner_headers,
        json={
            "email": "ordinary@example.com",
            "workspace_assignments": [{"workspace_id": workspace["id"], "role": "member"}],
        },
    ).json()
    accepted = admin_client.post(
        f"/auth/invitations/{_invite_token(invitation['invite_url'])}/accept",
        json={"full_name": "Ordinary Member", "password": "member123"},
    ).json()
    member_headers = {
        "Authorization": f"Bearer {accepted['session_token']}",
        "X-Workspace-ID": str(workspace["id"]),
    }
    payload = {"text": "Shared material", "source": "web", "title": "Plan", "tag_ids": []}

    denied = admin_client.post("/news/ingest/context", headers=member_headers, json=payload)
    assert denied.status_code == 403

    monkeypatch.setattr(admin, "ingest_workspace_text", lambda *args, **kwargs: 1)
    admin_headers = {**owner_headers, "X-Workspace-ID": str(workspace["id"])}
    created = admin_client.post("/admin/context", headers=admin_headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["chunks_indexed"] == 1

    with Session(get_engine()) as session:
        event = session.exec(
            select(OrganizationAuditEvent).where(
                OrganizationAuditEvent.action == "shared_context.created"
            )
        ).one()
        assert event.target_id == str(workspace["id"])


def test_invitation_is_hash_only_single_use_and_assigns_workspace(admin_client: TestClient) -> None:
    owner = _signup_organization(admin_client)
    headers = _headers(owner)
    workspace = admin_client.post(
        "/admin/workspaces", headers=headers, json={"name": "Research"}
    ).json()

    created = admin_client.post(
        "/admin/invitations",
        headers=headers,
        json={
            "email": "invitee@example.com",
            "organization_role": "member",
            "workspace_assignments": [{"workspace_id": workspace["id"], "role": "member"}],
        },
    )
    assert created.status_code == 201, created.text
    invitation = created.json()
    assert invitation["status"] == "pending"
    assert invitation["invite_url"]
    assert invitation["email_delivery_status"] == "not_configured"
    raw_token = _invite_token(invitation["invite_url"])

    with Session(get_engine()) as session:
        stored = session.get(OrganizationInvitation, invitation["id"])
        assert stored is not None
        assert stored.token_hash == hash_session_token(raw_token)
        assert raw_token not in stored.token_hash

    inspected = admin_client.get(f"/auth/invitations/{raw_token}")
    assert inspected.status_code == 200
    assert inspected.json()["existing_user"] is False
    assert inspected.json()["email"] == "invitee@example.com"

    accepted = admin_client.post(
        f"/auth/invitations/{raw_token}/accept",
        json={"full_name": "Invited Member", "password": "member123"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["session_token"]

    reused = admin_client.post(
        f"/auth/invitations/{raw_token}/accept",
        json={"full_name": "Invited Member", "password": "member123"},
    )
    assert reused.status_code in {400, 409, 410}

    with Session(get_engine()) as session:
        invited_user = session.exec(select(User).where(User.email == "invitee@example.com")).one()
        org_membership = session.exec(
            select(OrganizationMembership).where(OrganizationMembership.user_id == invited_user.id)
        ).one()
        workspace_membership = session.exec(
            select(WorkspaceMembership).where(WorkspaceMembership.user_id == invited_user.id)
        ).one()
        assert org_membership.organization_id == owner["organization"]["id"]
        assert workspace_membership.workspace_id == workspace["id"]


def test_resending_invalidates_old_token_and_revocation_blocks_acceptance(
    admin_client: TestClient,
) -> None:
    owner = _signup_organization(admin_client)
    headers = _headers(owner)
    created = admin_client.post(
        "/admin/invitations",
        headers=headers,
        json={"email": "resend@example.com"},
    ).json()
    old_token = _invite_token(created["invite_url"])

    listed = admin_client.get("/admin/invitations", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["invite_url"] is None

    resent = admin_client.post(
        f"/admin/invitations/{created['id']}/resend", headers=headers
    )
    assert resent.status_code == 200, resent.text
    new_token = _invite_token(resent.json()["invite_url"])
    assert new_token != old_token
    assert admin_client.get(f"/auth/invitations/{old_token}").status_code == 404

    revoked = admin_client.delete(f"/admin/invitations/{created['id']}", headers=headers)
    assert revoked.status_code == 204
    inspection = admin_client.get(f"/auth/invitations/{new_token}")
    assert inspection.status_code == 200
    assert inspection.json()["status"] == "revoked"
    rejected = admin_client.post(
        f"/auth/invitations/{new_token}/accept",
        json={"full_name": "Resent User", "password": "secret123"},
    )
    assert rejected.status_code == 409


def test_existing_user_must_sign_in_with_invited_email(admin_client: TestClient) -> None:
    existing = admin_client.post(
        "/auth/signup",
        json={"full_name": "Existing", "email": "existing@example.com", "password": "secret123"},
    )
    assert existing.status_code == 201
    owner = _signup_organization(admin_client)
    invitation = admin_client.post(
        "/admin/invitations",
        headers=_headers(owner),
        json={"email": "existing@example.com"},
    ).json()
    token = _invite_token(invitation["invite_url"])
    assert admin_client.get(f"/auth/invitations/{token}").json()["existing_user"] is True

    unsigned = admin_client.post(f"/auth/invitations/{token}/accept", json={})
    assert unsigned.status_code == 403

    wrong_user = _signup_organization(
        admin_client,
        email="wrong@example.com",
        organization_name="Wrong Organization",
    )
    wrong_email = admin_client.post(
        f"/auth/invitations/{token}/accept", headers=_headers(wrong_user), json={}
    )
    assert wrong_email.status_code == 403

    login = admin_client.post(
        "/auth/login", json={"email": "existing@example.com", "password": "secret123"}
    ).json()
    accepted = admin_client.post(
        f"/auth/invitations/{token}/accept",
        headers={"Authorization": f"Bearer {login['session_token']}"},
        json={},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["session_token"] is None


def test_email_delivery_failure_preserves_copyable_invitation(
    admin_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_delivery(**kwargs) -> MailDeliveryResult:
        return MailDeliveryResult(status="failed", error="SMTP unavailable")

    monkeypatch.setattr(organization_admin, "send_invitation_email", fail_delivery)
    owner = _signup_organization(admin_client)
    response = admin_client.post(
        "/admin/invitations",
        headers=_headers(owner),
        json={"email": "fallback@example.com"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["email_delivery_status"] == "failed"
    assert payload["email_delivery_error"] == "SMTP unavailable"
    assert payload["invite_url"]
    assert admin_client.get(
        f"/auth/invitations/{_invite_token(payload['invite_url'])}"
    ).status_code == 200


def test_member_update_is_atomic_protects_last_admin_and_revokes_sessions(
    admin_client: TestClient,
) -> None:
    owner = _signup_organization(admin_client)
    owner_headers = _headers(owner)
    workspace = admin_client.post(
        "/admin/workspaces", headers=owner_headers, json={"name": "Operations"}
    ).json()
    invitation = admin_client.post(
        "/admin/invitations",
        headers=owner_headers,
        json={
            "email": "member@example.com",
            "workspace_assignments": [{"workspace_id": workspace["id"], "role": "member"}],
        },
    ).json()
    accepted = admin_client.post(
        f"/auth/invitations/{_invite_token(invitation['invite_url'])}/accept",
        json={"full_name": "Member", "password": "member123"},
    ).json()
    member_token = accepted["session_token"]

    members = admin_client.get("/admin/members", headers=owner_headers).json()["items"]
    member = next(item for item in members if item["email"] == "member@example.com")

    with Session(get_engine()) as session:
        other_org = Organization(name="Other", slug="other")
        session.add(other_org)
        session.flush()
        invalid_workspace = Workspace(
            organization_id=other_org.id, name="Foreign", slug="foreign"
        )
        session.add(invalid_workspace)
        session.commit()
        invalid_workspace_id = invalid_workspace.id

    invalid = admin_client.put(
        f"/admin/members/{member['user_id']}",
        headers=owner_headers,
        json={
            "organization_role": "organization_admin",
            "workspace_assignments": [
                {"workspace_id": invalid_workspace_id, "role": "workspace_admin"}
            ],
        },
    )
    assert invalid.status_code in {400, 404}

    unchanged = admin_client.get("/admin/members", headers=owner_headers).json()["items"]
    unchanged_member = next(item for item in unchanged if item["user_id"] == member["user_id"])
    assert unchanged_member["organization_role"] == "member"
    assert unchanged_member["workspace_assignments"][0]["role"] == "member"

    deactivate = admin_client.put(
        f"/admin/members/{member['user_id']}",
        headers=owner_headers,
        json={"is_active": False},
    )
    assert deactivate.status_code == 200, deactivate.text
    status = admin_client.get(
        "/auth/status", headers={"Authorization": f"Bearer {member_token}"}
    )
    assert status.status_code == 200
    assert status.json()["authenticated"] is False

    owner_id = owner["user_id"]
    last_admin = admin_client.put(
        f"/admin/members/{owner_id}",
        headers=owner_headers,
        json={"organization_role": "member"},
    )
    assert last_admin.status_code in {400, 409}


def test_non_admin_cannot_mutate_and_audit_summaries_exclude_secrets(admin_client: TestClient) -> None:
    owner = _signup_organization(admin_client)
    owner_headers = _headers(owner)
    invitation = admin_client.post(
        "/admin/invitations",
        headers=owner_headers,
        json={"email": "reader@example.com"},
    ).json()
    raw_token = _invite_token(invitation["invite_url"])
    accepted = admin_client.post(
        f"/auth/invitations/{raw_token}/accept",
        json={"full_name": "Reader", "password": "highly-secret-password"},
    ).json()
    reader_headers = {"Authorization": f"Bearer {accepted['session_token']}"}

    forbidden = admin_client.patch(
        "/admin/organization", headers=reader_headers, json={"name": "Hijacked"}
    )
    assert forbidden.status_code == 403

    audit = admin_client.get("/admin/audit", headers=owner_headers)
    assert audit.status_code == 200
    serialized = audit.text
    assert raw_token not in serialized
    assert "highly-secret-password" not in serialized
    assert "token_hash" not in serialized

    with Session(get_engine()) as session:
        summaries = "\n".join(event.summary_json for event in session.exec(select(OrganizationAuditEvent)))
        assert raw_token not in summaries
        assert "highly-secret-password" not in summaries
