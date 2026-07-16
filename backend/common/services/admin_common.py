from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import func
from sqlmodel import Session, select

from backend.common.models.sql import (
    Organization,
    OrganizationAuditEvent,
    OrganizationMembership,
    Workspace,
    WorkspaceMembership,
)


ORG_ADMIN = "organization_admin"
WORKSPACE_ADMIN = "workspace_admin"


@dataclass(frozen=True)
class AdminScope:
    organization: Organization
    membership: OrganizationMembership
    managed_workspace_ids: frozenset[int]

    @property
    def is_organization_admin(self) -> bool:
        return self.membership.role == ORG_ADMIN


def slugify(value: str, *, fallback: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")[:100]
    return slug or fallback


def unique_organization_slug(session: Session, name: str) -> str:
    base = slugify(name, fallback="organization")
    candidate = base
    counter = 2
    while session.exec(select(Organization.id).where(Organization.slug == candidate)).first() is not None:
        suffix = f"-{counter}"
        candidate = f"{base[:120 - len(suffix)]}{suffix}"
        counter += 1
    return candidate


def unique_workspace_slug(session: Session, organization_id: int, name: str) -> str:
    base = slugify(name, fallback="workspace")
    candidate = base
    counter = 2
    while session.exec(
        select(Workspace.id).where(
            Workspace.organization_id == organization_id,
            Workspace.slug == candidate,
        )
    ).first() is not None:
        suffix = f"-{counter}"
        candidate = f"{base[:120 - len(suffix)]}{suffix}"
        counter += 1
    return candidate


def add_audit_event(
    session: Session,
    *,
    organization_id: int,
    actor_user_id: int | None,
    action: str,
    target_type: str,
    target_id: int | str | None,
    summary: dict | None = None,
) -> OrganizationAuditEvent:
    event = OrganizationAuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        summary_json=json.dumps(summary or {}, ensure_ascii=True, sort_keys=True),
    )
    session.add(event)
    return event


def active_organization_membership(session: Session, user_id: int) -> OrganizationMembership:
    memberships = session.exec(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == user_id, OrganizationMembership.is_active)
        .order_by(OrganizationMembership.id)
    ).all()
    if not memberships:
        raise PermissionError("Active organization membership required")
    if len(memberships) > 1:
        raise PermissionError("Account has conflicting active organization memberships")
    return memberships[0]


def get_admin_scope(session: Session, user_id: int) -> AdminScope:
    membership = active_organization_membership(session, user_id)
    organization = session.get(Organization, membership.organization_id)
    if organization is None:
        raise PermissionError("Organization not found")
    workspace_admin_ids = {
        int(value)
        for value in session.exec(
            select(WorkspaceMembership.workspace_id)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.is_active,
                WorkspaceMembership.role == WORKSPACE_ADMIN,
                Workspace.organization_id == organization.id,
            )
        ).all()
    }
    if membership.role != ORG_ADMIN and not workspace_admin_ids:
        raise PermissionError("Organization administration permission required")
    return AdminScope(
        organization=organization,
        membership=membership,
        managed_workspace_ids=frozenset(workspace_admin_ids),
    )


def visible_workspaces(session: Session, scope: AdminScope) -> list[tuple[Workspace, str, int, int]]:
    workspaces = session.exec(
        select(Workspace)
        .where(Workspace.organization_id == scope.organization.id)
        .order_by(Workspace.name, Workspace.id)
    ).all()
    memberships = {
        item.workspace_id: item
        for item in session.exec(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == scope.membership.user_id,
                WorkspaceMembership.is_active,
            )
        ).all()
    }
    if not scope.is_organization_admin:
        workspaces = [item for item in workspaces if item.id in scope.managed_workspace_ids]
    results: list[tuple[Workspace, str, int, int]] = []
    for workspace in workspaces:
        count = session.exec(
            select(func.count(WorkspaceMembership.id)).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.is_active,
            )
        ).one()
        admin_count = session.exec(
            select(func.count(WorkspaceMembership.id)).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.is_active,
                WorkspaceMembership.role == WORKSPACE_ADMIN,
            )
        ).one()
        own_membership = memberships.get(workspace.id)
        role = WORKSPACE_ADMIN if scope.is_organization_admin else own_membership.role
        results.append((workspace, role, int(count), int(admin_count)))
    return results
