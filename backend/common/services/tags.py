from __future__ import annotations

import re

from sqlmodel import Session, select

from backend.common.models.sql import (
    ContextTag,
    OrganizationMembership,
    Tag,
    UserTagPreference,
    Workspace,
    WorkspaceMembership,
    WorkspaceTagPolicy,
)


def normalize_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")[:120]


def create_tag(session: Session, *, organization_id: int, display_name: str) -> Tag:
    key = normalize_tag(display_name)
    if not key:
        raise ValueError("Tag name is empty")
    existing = session.exec(
        select(Tag).where(Tag.organization_id == organization_id, Tag.normalized_key == key)
    ).first()
    if existing is not None:
        return existing
    tag = Tag(organization_id=organization_id, normalized_key=key, display_name=display_name.strip())
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


def list_workspace_tags(session: Session, *, workspace_id: int, user_id: int) -> list[Tag]:
    workspace = session.get(Workspace, workspace_id)
    membership = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.is_active,
        )
    ).first()
    if workspace is None or membership is None:
        raise PermissionError("Workspace access denied")
    return list(
        session.exec(
            select(Tag)
            .where(Tag.organization_id == workspace.organization_id)
            .order_by(Tag.normalized_key)
        ).all()
    )


def set_user_tag_preference(
    session: Session,
    *,
    user_id: int,
    tag_id: int,
    weight: float,
    muted: bool,
) -> UserTagPreference:
    tag = session.get(Tag, tag_id)
    if tag is None or tag.organization_id is None or not _is_org_member(session, tag.organization_id, user_id):
        raise PermissionError("Tag access denied")
    preference = session.exec(
        select(UserTagPreference).where(
            UserTagPreference.user_id == user_id,
            UserTagPreference.tag_id == tag_id,
        )
    ).first()
    if preference is None:
        preference = UserTagPreference(user_id=user_id, tag_id=tag_id)
    preference.weight = max(-1.0, min(1.0, weight))
    preference.muted = muted
    session.add(preference)
    session.commit()
    session.refresh(preference)
    return preference


def set_workspace_tag_policy(
    session: Session,
    *,
    workspace_id: int,
    actor_user_id: int,
    tag_id: int,
    priority: float,
    blocked: bool,
) -> WorkspaceTagPolicy:
    workspace = session.get(Workspace, workspace_id)
    tag = session.get(Tag, tag_id)
    if workspace is None or tag is None or tag.organization_id != workspace.organization_id:
        raise ValueError("Workspace or tag not found")
    if not _is_workspace_admin(session, workspace_id, workspace.organization_id, actor_user_id):
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
    session.commit()
    session.refresh(policy)
    return policy


def feed_tag_adjustment(
    session: Session,
    *,
    event_id: int,
    user_id: int,
    workspace_id: int | None,
) -> tuple[bool, float]:
    """Return whether tags hide a card and a bounded personal/team score adjustment."""
    tag_ids = list(session.exec(select(ContextTag.tag_id).where(ContextTag.event_id == event_id)).all())
    if not tag_ids:
        return False, 0.0
    preferences = session.exec(
        select(UserTagPreference).where(
            UserTagPreference.user_id == user_id,
            UserTagPreference.tag_id.in_(tag_ids),
        )
    ).all()
    policies = session.exec(
        select(WorkspaceTagPolicy).where(
            WorkspaceTagPolicy.workspace_id == workspace_id,
            WorkspaceTagPolicy.tag_id.in_(tag_ids),
        )
    ).all() if workspace_id is not None else []
    muted = any(item.muted for item in preferences) or any(item.blocked for item in policies)
    adjustment = 0.15 * (sum(item.weight for item in preferences) + sum(item.priority for item in policies))
    return muted, max(-0.5, min(0.5, adjustment))


def _is_org_member(session: Session, organization_id: int, user_id: int) -> bool:
    return session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.is_active,
        )
    ).first() is not None


def _is_workspace_admin(session: Session, workspace_id: int, organization_id: int, user_id: int) -> bool:
    org = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.is_active,
        )
    ).first()
    if org is not None and org.role == "organization_admin":
        return True
    workspace = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.role == "workspace_admin",
            WorkspaceMembership.is_active,
        )
    ).first()
    return workspace is not None
