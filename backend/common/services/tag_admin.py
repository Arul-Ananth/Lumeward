from __future__ import annotations

from sqlmodel import Session, select

from backend.common.models.sql import Tag, Workspace, WorkspaceTagPolicy
from backend.common.services.admin_common import AdminScope, add_audit_event
from backend.common.services.tags import normalize_tag


def create_admin_tag(session: Session, scope: AdminScope, display_name: str) -> Tag:
    if not scope.is_organization_admin:
        raise PermissionError("Organization administration permission required")
    key = normalize_tag(display_name)
    if not key:
        raise ValueError("Tag name is empty")
    existing = session.exec(
        select(Tag).where(
            Tag.organization_id == scope.organization.id,
            Tag.normalized_key == key,
        )
    ).first()
    if existing is not None:
        return existing

    tag = Tag(
        organization_id=int(scope.organization.id),
        normalized_key=key,
        display_name=display_name.strip(),
    )
    session.add(tag)
    session.flush()
    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="tag.created",
        target_type="tag",
        target_id=tag.id,
        summary={"display_name": tag.display_name},
    )
    session.commit()
    session.refresh(tag)
    return tag


def set_admin_workspace_tag_policy(
    session: Session,
    scope: AdminScope,
    *,
    workspace_id: int,
    tag_id: int,
    priority: float,
    blocked: bool,
) -> WorkspaceTagPolicy:
    workspace = session.get(Workspace, workspace_id)
    tag = session.get(Tag, tag_id)
    if workspace is None or tag is None or workspace.organization_id != scope.organization.id:
        raise ValueError("Workspace or tag not found")
    if tag.organization_id != scope.organization.id:
        raise ValueError("Workspace or tag not found")
    if not scope.is_organization_admin and workspace_id not in scope.managed_workspace_ids:
        raise PermissionError("Workspace administration permission required")

    policy = session.exec(
        select(WorkspaceTagPolicy).where(
            WorkspaceTagPolicy.workspace_id == workspace_id,
            WorkspaceTagPolicy.tag_id == tag_id,
        )
    ).first()
    if policy is None:
        policy = WorkspaceTagPolicy(workspace_id=workspace_id, tag_id=tag_id)
    policy.priority = max(-1.0, min(1.0, priority))
    policy.blocked = blocked
    session.add(policy)
    session.flush()
    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="workspace_tag_policy.updated",
        target_type="workspace_tag_policy",
        target_id=policy.id,
        summary={"workspace_id": workspace_id, "tag_id": tag_id},
    )
    session.commit()
    session.refresh(policy)
    return policy
