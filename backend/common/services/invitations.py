from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from backend.common.config import settings
from backend.common.models.admin_schemas import InvitationAccept, InvitationCreate
from backend.common.models.sql import (
    AuthIdentity,
    InvitationWorkspaceAssignment,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    User,
    Workspace,
    WorkspaceMembership,
)
from backend.common.services.admin_common import AdminScope, add_audit_event
from backend.common.services.auth.auth_utils import get_password_hash
from backend.common.services.auth.store import INTERACTIVE_PROVIDER, get_user_by_email, hash_session_token
from backend.common.services.auth.types import AuthPrincipal
from backend.common.services.invitation_mail import invitation_url, send_invitation_email
from backend.common.services.membership_admin import _validate_assignments
from backend.common.services.organization_setup import _new_session


def workspace_assignments_for_invitation(
    session: Session,
    invitation_id: int,
) -> list[tuple[InvitationWorkspaceAssignment, Workspace]]:
    return list(
        session.exec(
            select(InvitationWorkspaceAssignment, Workspace)
            .join(Workspace, Workspace.id == InvitationWorkspaceAssignment.workspace_id)
            .where(InvitationWorkspaceAssignment.invitation_id == invitation_id)
            .order_by(Workspace.name)
        ).all()
    )


def effective_invitation_status(invitation: OrganizationInvitation) -> str:
    if invitation.status == "pending" and invitation.expires_at < datetime.utcnow():
        return "expired"
    return invitation.status


def _issue_invitation(
    session: Session,
    scope: AdminScope,
    request: InvitationCreate,
) -> tuple[OrganizationInvitation, str]:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    email = str(request.email).strip().lower()
    requested = _validate_assignments(
        session,
        scope,
        request.workspace_assignments,
        organization_admin=True,
    )
    user = get_user_by_email(session, email)
    if user is not None:
        existing_membership = session.exec(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == scope.organization.id,
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.is_active,
            )
        ).first()
        if existing_membership is not None:
            raise ValueError("User is already an active organization member")
        other_membership = session.exec(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.is_active,
                OrganizationMembership.organization_id != scope.organization.id,
            )
        ).first()
        if other_membership is not None:
            raise ValueError("User already belongs to another active organization")
    pending = session.exec(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == scope.organization.id,
            OrganizationInvitation.email == email,
            OrganizationInvitation.status == "pending",
        )
    ).first()
    if pending is not None and effective_invitation_status(pending) == "pending":
        raise ValueError("A pending invitation already exists for this email")
    if pending is not None:
        pending.status = "expired"
        pending.updated_at = datetime.utcnow()
        session.add(pending)

    raw_token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=int(scope.organization.id),
        email=email,
        organization_role=request.organization_role,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.INVITATION_EXPIRE_DAYS),
        invited_by_user_id=scope.membership.user_id,
    )
    session.add(invitation)
    session.flush()
    session.add_all(
        InvitationWorkspaceAssignment(
            invitation_id=int(invitation.id),
            workspace_id=workspace_id,
            role=item.role,
        )
        for workspace_id, item in requested.items()
    )
    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="invitation.created",
        target_type="invitation",
        target_id=invitation.id,
        summary={"email": email, "organization_role": request.organization_role},
    )
    session.commit()
    session.refresh(invitation)
    return invitation, raw_token


def create_invitation(
    session: Session,
    scope: AdminScope,
    request: InvitationCreate,
    *,
    deliver=send_invitation_email,
) -> tuple[OrganizationInvitation, str]:
    invitation, raw_token = _issue_invitation(session, scope, request)
    delivery = deliver(
        recipient=invitation.email,
        organization_name=scope.organization.name,
        raw_token=raw_token,
    )
    invitation.email_delivery_status = delivery.status
    invitation.email_delivery_error = delivery.error
    invitation.updated_at = datetime.utcnow()
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    return invitation, invitation_url(raw_token)


def list_invitations(
    session: Session,
    scope: AdminScope,
    *,
    page: int,
    page_size: int,
) -> tuple[list[OrganizationInvitation], int]:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    all_items = list(
        session.exec(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == scope.organization.id)
            .order_by(OrganizationInvitation.created_at.desc(), OrganizationInvitation.id.desc())
        ).all()
    )
    return all_items[(page - 1) * page_size: page * page_size], len(all_items)


def resend_invitation(
    session: Session,
    scope: AdminScope,
    invitation_id: int,
    *,
    deliver=send_invitation_email,
) -> tuple[OrganizationInvitation, str]:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    invitation = session.get(OrganizationInvitation, invitation_id)
    if invitation is None or invitation.organization_id != scope.organization.id:
        raise ValueError("Invitation not found")
    if invitation.status in {"accepted", "revoked"}:
        raise ValueError("Only pending or expired invitations can be resent")
    raw_token = secrets.token_urlsafe(32)
    invitation.token_hash = hash_session_token(raw_token)
    invitation.status = "pending"
    invitation.expires_at = datetime.utcnow() + timedelta(days=settings.INVITATION_EXPIRE_DAYS)
    invitation.email_delivery_status = "pending"
    invitation.email_delivery_error = None
    invitation.updated_at = datetime.utcnow()
    session.add(invitation)
    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="invitation.resent",
        target_type="invitation",
        target_id=invitation.id,
        summary={"email": invitation.email},
    )
    session.commit()
    delivery = deliver(
        recipient=invitation.email,
        organization_name=scope.organization.name,
        raw_token=raw_token,
    )
    invitation.email_delivery_status = delivery.status
    invitation.email_delivery_error = delivery.error
    invitation.updated_at = datetime.utcnow()
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    return invitation, invitation_url(raw_token)


def revoke_invitation(session: Session, scope: AdminScope, invitation_id: int) -> None:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    invitation = session.get(OrganizationInvitation, invitation_id)
    if invitation is None or invitation.organization_id != scope.organization.id:
        raise ValueError("Invitation not found")
    if invitation.status == "accepted":
        raise ValueError("Accepted invitations cannot be revoked")
    if invitation.status == "revoked":
        return
    invitation.status = "revoked"
    invitation.revoked_at = datetime.utcnow()
    invitation.updated_at = invitation.revoked_at
    session.add(invitation)
    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="invitation.revoked",
        target_type="invitation",
        target_id=invitation.id,
        summary={"email": invitation.email},
    )
    session.commit()


def invitation_by_token(
    session: Session,
    raw_token: str,
    *,
    for_update: bool = False,
) -> OrganizationInvitation:
    statement = select(OrganizationInvitation).where(
        OrganizationInvitation.token_hash == hash_session_token(raw_token)
    )
    if for_update:
        statement = statement.with_for_update()
    invitation = session.exec(statement).first()
    if invitation is None:
        raise ValueError("Invitation not found")
    return invitation


def accept_invitation(
    session: Session,
    invitation: OrganizationInvitation,
    request: InvitationAccept,
    principal: AuthPrincipal | None,
) -> tuple[Organization, str | None]:
    if effective_invitation_status(invitation) != "pending":
        raise ValueError("Invitation is no longer valid")
    organization = session.get(Organization, invitation.organization_id)
    if organization is None:
        raise ValueError("Organization not found")
    user = get_user_by_email(session, invitation.email)
    raw_session_token: str | None = None
    if user is None:
        if request.full_name is None or request.password is None:
            raise ValueError("Full name and password are required for a new account")
        password_hash = get_password_hash(request.password)
        user = User(
            email=invitation.email,
            full_name=request.full_name.strip(),
            hashed_password=password_hash,
        )
        session.add(user)
        session.flush()
        identity = AuthIdentity(
            user_id=int(user.id),
            provider=INTERACTIVE_PROVIDER,
            subject=invitation.email,
            email=invitation.email,
            password_hash=password_hash,
        )
        session.add(identity)
        session.flush()
        _auth_session, raw_session_token = _new_session(session, user=user, identity=identity)
    else:
        if principal is None or principal.user_id != user.id:
            raise PermissionError("Sign in with the invited email before accepting")
        if request.full_name is not None or request.password is not None:
            raise ValueError("Existing accounts must accept the invitation while signed in")

    active_elsewhere = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.is_active,
            OrganizationMembership.organization_id != organization.id,
        )
    ).first()
    if active_elsewhere is not None:
        raise ValueError("User already belongs to another active organization")
    membership = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.user_id == user.id,
        )
    ).first()
    if membership is None:
        membership = OrganizationMembership(organization_id=int(organization.id), user_id=int(user.id))
    membership.role = invitation.organization_role
    membership.is_active = True
    session.add(membership)

    for assignment, workspace in workspace_assignments_for_invitation(session, int(invitation.id)):
        workspace_membership = session.exec(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == user.id,
            )
        ).first()
        if workspace_membership is None:
            workspace_membership = WorkspaceMembership(
                workspace_id=int(workspace.id),
                user_id=int(user.id),
            )
        workspace_membership.role = assignment.role
        workspace_membership.is_active = True
        session.add(workspace_membership)

    now = datetime.utcnow()
    invitation.status = "accepted"
    invitation.accepted_by_user_id = int(user.id)
    invitation.accepted_at = now
    invitation.updated_at = now
    session.add(invitation)
    add_audit_event(
        session,
        organization_id=int(organization.id),
        actor_user_id=int(user.id),
        action="invitation.accepted",
        target_type="invitation",
        target_id=invitation.id,
        summary={"user_id": user.id},
    )
    session.commit()
    return organization, raw_session_token
