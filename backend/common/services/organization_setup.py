from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlmodel import Session

from backend.common.config import settings
from backend.common.models.admin_schemas import OrganizationSignupRequest
from backend.common.models.sql import (
    AuthIdentity,
    AuthSession,
    Organization,
    OrganizationMembership,
    User,
    Workspace,
    WorkspaceMembership,
)
from backend.common.services.admin_common import (
    AdminScope,
    ORG_ADMIN,
    WORKSPACE_ADMIN,
    add_audit_event,
    unique_organization_slug,
    unique_workspace_slug,
)
from backend.common.services.auth.auth_utils import get_password_hash
from backend.common.services.auth.store import (
    INTERACTIVE_PROVIDER,
    SESSION_TRANSPORT,
    get_user_by_email,
    hash_session_token,
)


def _new_session(session: Session, *, user: User, identity: AuthIdentity) -> tuple[AuthSession, str]:
    raw_token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    auth_session = AuthSession(
        user_id=int(user.id),
        identity_id=int(identity.id),
        transport=SESSION_TRANSPORT,
        token_hash=hash_session_token(raw_token),
        expires_at=now + timedelta(minutes=settings.AUTH_SESSION_EXPIRE_MINUTES),
        last_used_at=now,
    )
    session.add(auth_session)
    return auth_session, raw_token


def signup_organization(
    session: Session,
    request: OrganizationSignupRequest,
    *,
    new_session=_new_session,
) -> tuple[User, Organization, str]:
    email = str(request.email).strip().lower()
    if get_user_by_email(session, email) is not None:
        raise ValueError("Email exists")
    password_hash = get_password_hash(request.password)
    user = User(email=email, full_name=request.full_name.strip(), hashed_password=password_hash)
    organization = Organization(
        name=request.organization_name.strip(),
        slug=unique_organization_slug(session, request.organization_name),
    )
    try:
        session.add_all([user, organization])
        session.flush()
        identity = AuthIdentity(
            user_id=int(user.id),
            provider=INTERACTIVE_PROVIDER,
            subject=email,
            email=email,
            password_hash=password_hash,
        )
        session.add(identity)
        session.flush()
        session.add(
            OrganizationMembership(
                organization_id=int(organization.id),
                user_id=int(user.id),
                role=ORG_ADMIN,
            )
        )
        add_audit_event(
            session,
            organization_id=int(organization.id),
            actor_user_id=int(user.id),
            action="organization.created",
            target_type="organization",
            target_id=organization.id,
            summary={"name": organization.name},
        )
        _auth_session, raw_token = new_session(session, user=user, identity=identity)
        session.commit()
        session.refresh(user)
        session.refresh(organization)
    except Exception:
        session.rollback()
        raise
    return user, organization, raw_token


def rename_organization(session: Session, scope: AdminScope, name: str) -> Organization:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    old_name = scope.organization.name
    scope.organization.name = name.strip()
    session.add(scope.organization)
    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="organization.renamed",
        target_type="organization",
        target_id=scope.organization.id,
        summary={"from": old_name, "to": scope.organization.name},
    )
    session.commit()
    session.refresh(scope.organization)
    return scope.organization


def create_admin_workspace(session: Session, scope: AdminScope, name: str) -> Workspace:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    workspace = Workspace(
        organization_id=int(scope.organization.id),
        name=name.strip(),
        slug=unique_workspace_slug(session, int(scope.organization.id), name),
    )
    session.add(workspace)
    session.flush()
    session.add(
        WorkspaceMembership(
            workspace_id=int(workspace.id),
            user_id=scope.membership.user_id,
            role=WORKSPACE_ADMIN,
        )
    )
    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="workspace.created",
        target_type="workspace",
        target_id=workspace.id,
        summary={"name": workspace.name},
    )
    session.commit()
    session.refresh(workspace)
    return workspace


def rename_workspace(session: Session, scope: AdminScope, workspace_id: int, name: str) -> Workspace:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.organization_id != scope.organization.id:
        raise ValueError("Workspace not found")
    if not scope.is_organization_admin and workspace_id not in scope.managed_workspace_ids:
        raise PermissionError("Workspace administration permission required")
    old_name = workspace.name
    workspace.name = name.strip()
    session.add(workspace)
    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="workspace.renamed",
        target_type="workspace",
        target_id=workspace.id,
        summary={"from": old_name, "to": workspace.name},
    )
    session.commit()
    session.refresh(workspace)
    return workspace
