from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, select

from backend.common.models.sql import (
    ContextItem,
    ContextTag,
    EventRaw,
    OrganizationInvitation,
    OrganizationMembership,
    OrganizationAuditEvent,
    Tag,
    User,
    Workspace,
    WorkspaceTagPolicy,
)
from backend.common.services.admin_common import AdminScope


def list_shared_context(
    session: Session,
    scope: AdminScope,
    *,
    workspace_id: int,
    page: int,
    page_size: int,
) -> tuple[list[tuple[ContextItem, EventRaw | None, list[Tag]]], int]:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.organization_id != scope.organization.id:
        raise ValueError("Workspace not found")
    if not scope.is_organization_admin and workspace_id not in scope.managed_workspace_ids:
        raise PermissionError("Workspace administration permission required")
    items = list(
        session.exec(
            select(ContextItem)
            .where(
                ContextItem.organization_id == str(scope.organization.id),
                ContextItem.workspace_id == str(workspace_id),
                ContextItem.visibility == "workspace",
                ContextItem.deleted_at.is_(None),
            )
            .order_by(ContextItem.created_at.desc(), ContextItem.id.desc())
        ).all()
    )
    total = len(items)
    items = items[(page - 1) * page_size: page * page_size]
    results = []
    for item in items:
        event = session.get(EventRaw, item.event_id) if item.event_id is not None else None
        tags = []
        if event is not None:
            tags = list(
                session.exec(
                    select(Tag)
                    .join(ContextTag, ContextTag.tag_id == Tag.id)
                    .where(ContextTag.event_id == event.id)
                    .order_by(Tag.display_name)
                ).all()
            )
        results.append((item, event, tags))
    return results, total


def list_admin_tags(session: Session, scope: AdminScope, workspace_id: int | None) -> list[tuple[Tag, WorkspaceTagPolicy | None]]:
    if workspace_id is not None:
        workspace = session.get(Workspace, workspace_id)
        if workspace is None or workspace.organization_id != scope.organization.id:
            raise ValueError("Workspace not found")
        if not scope.is_organization_admin and workspace_id not in scope.managed_workspace_ids:
            raise PermissionError("Workspace administration permission required")
    tags = session.exec(
        select(Tag).where(Tag.organization_id == scope.organization.id).order_by(Tag.display_name)
    ).all()
    policies = {
        item.tag_id: item
        for item in session.exec(
            select(WorkspaceTagPolicy).where(WorkspaceTagPolicy.workspace_id == workspace_id)
        ).all()
    } if workspace_id is not None else {}
    return [(tag, policies.get(tag.id)) for tag in tags]


def list_audit_events(
    session: Session,
    scope: AdminScope,
    *,
    page: int,
    page_size: int,
    action: str | None,
) -> tuple[list[tuple[OrganizationAuditEvent, User | None]], int]:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    statement = select(OrganizationAuditEvent).where(
        OrganizationAuditEvent.organization_id == scope.organization.id
    )
    if action:
        statement = statement.where(OrganizationAuditEvent.action == action)
    events = list(session.exec(statement.order_by(OrganizationAuditEvent.created_at.desc())).all())
    total = len(events)
    events = events[(page - 1) * page_size: page * page_size]
    return [(event, session.get(User, event.actor_user_id) if event.actor_user_id else None) for event in events], total


def overview_counts(session: Session, scope: AdminScope) -> tuple[int, int, int, int]:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    member_count = session.exec(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == scope.organization.id,
            OrganizationMembership.is_active,
        )
    ).one()
    workspace_count = session.exec(
        select(func.count(Workspace.id)).where(Workspace.organization_id == scope.organization.id)
    ).one()
    pending_invitation_count = session.exec(
        select(func.count(OrganizationInvitation.id)).where(
            OrganizationInvitation.organization_id == scope.organization.id,
            OrganizationInvitation.status == "pending",
            OrganizationInvitation.expires_at >= datetime.utcnow(),
        )
    ).one()
    shared_context_count = session.exec(
        select(func.count(ContextItem.id)).where(
            ContextItem.organization_id == str(scope.organization.id),
            ContextItem.visibility == "workspace",
            ContextItem.deleted_at.is_(None),
        )
    ).one()
    return tuple(map(int, (member_count, workspace_count, pending_invitation_count, shared_context_count)))
