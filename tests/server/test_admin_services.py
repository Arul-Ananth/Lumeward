from __future__ import annotations

import pytest
from sqlmodel import Session, func, select

from backend.common.database import get_engine
from backend.common.models.admin_schemas import OrganizationSignupRequest
from backend.common.models.sql import (
    AuthIdentity,
    AuthSession,
    Organization,
    OrganizationAuditEvent,
    OrganizationMembership,
    User,
    Tag,
)
from backend.common.services import organization_admin
from backend.common.services import tag_admin
from backend.common.services.tag_admin import create_admin_tag


def test_organization_signup_rolls_back_every_record_when_session_creation_fails(
    isolated_data_dir,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_session_creation(*args, **kwargs):
        raise RuntimeError("forced session failure")

    monkeypatch.setattr(organization_admin, "_new_session", fail_session_creation)
    request = OrganizationSignupRequest(
        full_name="Rollback Owner",
        email="rollback@example.com",
        password="secret123",
        organization_name="Rollback Organization",
    )

    with Session(get_engine()) as session:
        with pytest.raises(RuntimeError, match="forced session failure"):
            organization_admin.signup_organization(session, request)

    with Session(get_engine()) as session:
        for model in (
            User,
            AuthIdentity,
            Organization,
            OrganizationMembership,
            OrganizationAuditEvent,
            AuthSession,
        ):
            assert session.exec(select(func.count(model.id))).one() == 0


def test_admin_scope_rejects_conflicting_active_organizations(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        user = User(email="conflict@example.com", full_name="Conflict", hashed_password="disabled")
        first = Organization(name="First", slug="first")
        second = Organization(name="Second", slug="second")
        session.add_all([user, first, second])
        session.flush()
        session.add_all(
            [
                OrganizationMembership(
                    organization_id=first.id,
                    user_id=user.id,
                    role="organization_admin",
                ),
                OrganizationMembership(
                    organization_id=second.id,
                    user_id=user.id,
                    role="member",
                ),
            ]
        )
        session.commit()

        with pytest.raises(PermissionError, match="conflicting active organization memberships"):
            organization_admin.get_admin_scope(session, user.id)


def test_tag_and_audit_roll_back_together(isolated_data_dir, monkeypatch: pytest.MonkeyPatch) -> None:
    request = OrganizationSignupRequest(
        full_name="Tag Owner",
        email="tag-owner@example.com",
        password="secret123",
        organization_name="Tag Organization",
    )
    with Session(get_engine()) as session:
        user, _organization, _token = organization_admin.signup_organization(session, request)
        scope = organization_admin.get_admin_scope(session, user.id)

        def fail_audit(*args, **kwargs):
            raise RuntimeError("forced audit failure")

        monkeypatch.setattr(tag_admin, "add_audit_event", fail_audit)
        with pytest.raises(RuntimeError, match="forced audit failure"):
            create_admin_tag(session, scope, "Security")
        session.rollback()

    with Session(get_engine()) as session:
        assert session.exec(select(Tag).where(Tag.normalized_key == "security")).first() is None
