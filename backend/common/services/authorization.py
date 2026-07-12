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
    roles = {row.role for row in org_memberships}
    workspace_rows = session.exec(
        select(WorkspaceMembership, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.is_active,
        )
    ).all()
    workspace_ids = tuple(
        int(workspace.id)
        for _membership, workspace in workspace_rows
        if workspace.id is not None and workspace.organization_id in organization_ids
    )
    roles.update(
        membership.role
        for membership, workspace in workspace_rows
        if workspace.organization_id in organization_ids
    )
    if requested_workspace_id is not None and requested_workspace_id not in workspace_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")
    return RequestContext(
        user_id=principal.user_id,
        organization_ids=tuple(sorted(organization_ids)),
        workspace_ids=workspace_ids,
        active_workspace_id=requested_workspace_id,
        roles=frozenset(roles),
    )


def get_workspace_memberships(session: Session, user_id: int) -> list[tuple[Workspace, str]]:
    rows = session.exec(
        select(Workspace, WorkspaceMembership.role)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.user_id == user_id, WorkspaceMembership.is_active)
        .order_by(Workspace.name)
    ).all()
    return [(workspace, role) for workspace, role in rows]


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
    if membership is None or membership.role not in {"organization_admin", "workspace_admin"}:
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
        session.commit()
        session.refresh(workspace)
    except Exception:
        session.rollback()
        raise ValueError("Workspace slug already exists")
    return workspace


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
