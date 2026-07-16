from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status
from sqlmodel import Session, select

from backend.common.models.sql import (
    OrganizationMembership,
    User,
    Workspace,
    WorkspaceMembership,
    Organization,
)
from backend.common.services.auth.types import AuthPrincipal
from backend.common.services.admin_common import add_audit_event


@dataclass(frozen=True)
class RequestContext:
    """Authenticated identity plus the workspace scopes allowed for a request."""

    user_id: int
    organization_ids: tuple[int, ...]
    workspace_ids: tuple[int, ...]
    active_workspace_id: int | None
    roles: frozenset[str]


def build_request_context(
    session: Session,
    principal: AuthPrincipal,
    requested_workspace_id: int | None = None,
) -> RequestContext:
    org_memberships = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == principal.user_id,
            OrganizationMembership.is_active,
        )
    ).all()
    organization_ids = {int(row.organization_id) for row in org_memberships}
    organization_roles = {int(row.organization_id): row.role for row in org_memberships}
    workspace_rows = session.exec(
        select(WorkspaceMembership, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.is_active,
        )
    ).all()
    eligible_workspaces = [
        (membership, workspace)
        for membership, workspace in workspace_rows
        if workspace.id is not None and workspace.organization_id in organization_ids
    ]
    eligible_workspace_ids = tuple(int(workspace.id) for _membership, workspace in eligible_workspaces)
    if requested_workspace_id is not None and requested_workspace_id not in eligible_workspace_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")

    # Roles must be evaluated for the selected workspace, not accumulated from
    # every workspace the user can access. Organization-level roles apply only
    # within the active workspace's organization.
    roles: set[str] = set()
    active_organization_id: int | None = None
    if requested_workspace_id is not None:
        for membership, workspace in eligible_workspaces:
            if workspace.id == requested_workspace_id:
                active_organization_id = int(workspace.organization_id)
                roles.add(membership.role)
                organization_role = organization_roles.get(int(workspace.organization_id))
                if organization_role:
                    roles.add(organization_role)
                break
    return RequestContext(
        user_id=principal.user_id,
        organization_ids=(active_organization_id,) if active_organization_id is not None else (),
        workspace_ids=(requested_workspace_id,) if requested_workspace_id is not None else (),
        active_workspace_id=requested_workspace_id,
        roles=frozenset(roles),
    )


def get_workspace_memberships(session: Session, user_id: int) -> list[tuple[Workspace, str, str]]:
    rows = session.exec(
        select(Workspace, WorkspaceMembership.role, OrganizationMembership.role)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .join(OrganizationMembership, OrganizationMembership.organization_id == Workspace.organization_id)
        .where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.is_active,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.is_active,
        )
        .order_by(Workspace.name)
    ).all()
    return [(workspace, workspace_role, organization_role) for workspace, workspace_role, organization_role in rows]


def require_workspace_role(context: RequestContext, *allowed_roles: str) -> None:
    if not context.active_workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active workspace is required")
    if allowed_roles and not context.roles.intersection(allowed_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace role is insufficient")


def create_organization_for_user(session: Session, *, user_id: int, name: str, slug: str) -> Organization:
    existing = session.exec(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user_id)
    ).first()
    if existing is not None:
        raise ValueError("User already belongs to an organization")
    organization = Organization(name=name, slug=slug)
    session.add(organization)
    try:
        session.flush()
        session.add(OrganizationMembership(
            organization_id=organization.id,
            user_id=user_id,
            role="organization_admin",
        ))
        add_audit_event(
            session,
            organization_id=int(organization.id),
            actor_user_id=user_id,
            action="organization.created",
            target_type="organization",
            target_id=organization.id,
            summary={"name": organization.name, "source": "legacy_api"},
        )
        session.commit()
        session.refresh(organization)
    except Exception:
        session.rollback()
        raise ValueError("Organization slug already exists")
    return organization


def create_workspace(
    session: Session,
    *,
    organization_id: int,
    actor_user_id: int,
    name: str,
    slug: str,
) -> Workspace:
    membership = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == actor_user_id,
            OrganizationMembership.is_active,
        )
    ).first()
    if membership is None or membership.role != "organization_admin":
        raise PermissionError("Organization administration permission required")
    workspace = Workspace(organization_id=organization_id, name=name, slug=slug)
    session.add(workspace)
    try:
        session.flush()
        session.add(WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=actor_user_id,
            role="workspace_admin",
        ))
        add_audit_event(
            session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="workspace.created",
            target_type="workspace",
            target_id=workspace.id,
            summary={"name": workspace.name, "source": "legacy_api"},
        )
        session.commit()
        session.refresh(workspace)
    except Exception:
        session.rollback()
        raise ValueError("Workspace slug already exists")
    return workspace


def add_organization_member(
    session: Session,
    *,
    organization_id: int,
    actor_user_id: int,
    email: str,
    role: str,
) -> OrganizationMembership:
    actor = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == actor_user_id,
            OrganizationMembership.role == "organization_admin",
            OrganizationMembership.is_active,
        )
    ).first()
    if actor is None:
        raise PermissionError("Organization administration permission required")
    user = session.exec(select(User).where(User.email == email.strip().lower())).first()
    if user is None:
        raise ValueError("User not found")
    other_active_membership = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.is_active,
            OrganizationMembership.organization_id != organization_id,
        )
    ).first()
    if other_active_membership is not None:
        raise ValueError("User already belongs to another active organization")
    membership = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
    ).first()
    if membership is None:
        membership = OrganizationMembership(organization_id=organization_id, user_id=user.id)
    membership.role = role
    membership.is_active = True
    session.add(membership)
    add_audit_event(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="member.updated",
        target_type="user",
        target_id=user.id,
        summary={"organization_role": role, "is_active": True, "source": "legacy_api"},
    )
    session.commit()
    session.refresh(membership)
    return membership


def add_workspace_member(
    session: Session,
    *,
    workspace_id: int,
    actor_user_id: int,
    email: str,
    role: str,
) -> WorkspaceMembership:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise ValueError("Workspace not found")
    actor = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == actor_user_id,
            WorkspaceMembership.is_active,
        )
    ).first()
    org_actor = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == workspace.organization_id,
            OrganizationMembership.user_id == actor_user_id,
            OrganizationMembership.is_active,
        )
    ).first()
    if (actor is None or actor.role != "workspace_admin") and (org_actor is None or org_actor.role != "organization_admin"):
        raise PermissionError("Workspace administration permission required")
    user = session.exec(select(User).where(User.email == email.strip().lower())).first()
    if user is None:
        raise ValueError("User not found")
    org_member = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == workspace.organization_id,
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.is_active,
        )
    ).first()
    if org_member is None:
        raise ValueError("User is not an organization member")
    membership = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user.id,
        )
    ).first()
    if membership is None:
        membership = WorkspaceMembership(workspace_id=workspace_id, user_id=user.id, role=role)
    else:
        membership.role = role
        membership.is_active = True
    session.add(membership)
    add_audit_event(
        session,
        organization_id=int(workspace.organization_id),
        actor_user_id=actor_user_id,
        action="workspace_member.updated",
        target_type="user",
        target_id=user.id,
        summary={"workspace_id": workspace_id, "role": role, "source": "legacy_api"},
    )
    session.commit()
    session.refresh(membership)
    return membership


def workspace_header(x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID")) -> int | None:
    if not x_workspace_id:
        return None
    try:
        return int(x_workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-Workspace-ID must be an integer") from exc
