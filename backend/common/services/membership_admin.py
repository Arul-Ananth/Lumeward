from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, select

from backend.common.models.admin_schemas import AdminMemberUpdate, WorkspaceAssignmentInput
from backend.common.models.sql import (
    AuthSession,
    Organization,
    OrganizationMembership,
    User,
    Workspace,
    WorkspaceMembership,
)
from backend.common.services.admin_common import AdminScope, ORG_ADMIN, add_audit_event


def list_members(
    session: Session,
    scope: AdminScope,
    *,
    page: int,
    page_size: int,
    search: str | None,
    workspace_id: int | None,
) -> tuple[list[tuple[OrganizationMembership, User, list[tuple[WorkspaceMembership, Workspace]]]], int]:
    selected_ids: set[int] | None = None
    if workspace_id is not None:
        workspace = session.get(Workspace, workspace_id)
        if workspace is None or workspace.organization_id != scope.organization.id:
            raise ValueError("Workspace not found")
        if not scope.is_organization_admin and workspace_id not in scope.managed_workspace_ids:
            raise PermissionError("Workspace administration permission required")
        selected_ids = {workspace_id}
    elif not scope.is_organization_admin:
        selected_ids = set(scope.managed_workspace_ids)

    statement = (
        select(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(OrganizationMembership.organization_id == scope.organization.id)
    )
    if search:
        pattern = f"%{search.strip().lower()}%"
        statement = statement.where(
            func.lower(User.full_name).like(pattern) | func.lower(User.email).like(pattern)
        )
    rows = list(session.exec(statement.order_by(User.full_name, User.id)).all())
    if selected_ids is not None:
        member_ids = set(
            session.exec(
                select(WorkspaceMembership.user_id).where(
                    WorkspaceMembership.workspace_id.in_(selected_ids),
                    WorkspaceMembership.is_active,
                )
            ).all()
        )
        rows = [row for row in rows if row[1].id in member_ids]
    total = len(rows)
    rows = rows[(page - 1) * page_size: page * page_size]

    results = []
    for membership, user in rows:
        assignments = list(
            session.exec(
                select(WorkspaceMembership, Workspace)
                .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
                .where(
                    WorkspaceMembership.user_id == user.id,
                    WorkspaceMembership.is_active,
                    Workspace.organization_id == scope.organization.id,
                )
                .order_by(Workspace.name)
            ).all()
        )
        if selected_ids is not None:
            assignments = [item for item in assignments if item[1].id in selected_ids]
        results.append((membership, user, assignments))
    return results, total


def _validate_assignments(
    session: Session,
    scope: AdminScope,
    assignments: list[WorkspaceAssignmentInput],
    *,
    organization_admin: bool,
) -> dict[int, WorkspaceAssignmentInput]:
    requested = {item.workspace_id: item for item in assignments}
    if len(requested) != len(assignments):
        raise ValueError("Each workspace may be assigned only once")
    workspaces = session.exec(select(Workspace).where(Workspace.id.in_(requested))).all() if requested else []
    if len(workspaces) != len(requested) or any(item.organization_id != scope.organization.id for item in workspaces):
        raise ValueError("Every workspace assignment must belong to the organization")
    if not organization_admin and not set(requested).issubset(scope.managed_workspace_ids):
        raise PermissionError("Workspace administration permission required")
    return requested


def _protect_last_admin(
    session: Session,
    scope: AdminScope,
    membership: OrganizationMembership,
    update: AdminMemberUpdate,
) -> None:
    removes_admin = (
        membership.is_active
        and membership.role == ORG_ADMIN
        and (update.is_active is False or (update.organization_role is not None and update.organization_role != ORG_ADMIN))
    )
    if not removes_admin:
        return
    others = session.exec(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == scope.organization.id,
            OrganizationMembership.is_active,
            OrganizationMembership.role == ORG_ADMIN,
            OrganizationMembership.user_id != membership.user_id,
        )
    ).one()
    if int(others) == 0:
        raise ValueError("The final active organization administrator cannot be demoted or deactivated")


def update_member(
    session: Session,
    scope: AdminScope,
    user_id: int,
    update: AdminMemberUpdate,
) -> OrganizationMembership:
    membership = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == scope.organization.id,
            OrganizationMembership.user_id == user_id,
        )
    ).first()
    if membership is None:
        raise ValueError("Organization member not found")
    if not scope.is_organization_admin and (update.organization_role is not None or update.is_active is not None):
        raise PermissionError("Organization administration permission required")
    if not scope.is_organization_admin and not membership.is_active:
        raise ValueError("Inactive organization members cannot be assigned to a workspace")
    if scope.is_organization_admin:
        # Serialize organization-level role/status changes so two concurrent
        # requests cannot both observe another administrator and remove the last two.
        session.exec(
            select(Organization)
            .where(Organization.id == scope.organization.id)
            .with_for_update()
        ).one()
        session.refresh(membership)
        _protect_last_admin(session, scope, membership, update)

    requested: dict[int, WorkspaceAssignmentInput] | None = None
    if update.workspace_assignments is not None:
        requested = _validate_assignments(
            session,
            scope,
            update.workspace_assignments,
            organization_admin=scope.is_organization_admin,
        )
    if update.is_active is True and not membership.is_active:
        other = session.exec(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.is_active,
                OrganizationMembership.organization_id != scope.organization.id,
            )
        ).first()
        if other is not None:
            raise ValueError("User already belongs to another active organization")
    if update.organization_role is not None:
        membership.role = update.organization_role
    if update.is_active is not None:
        membership.is_active = update.is_active
    session.add(membership)

    existing = {
        item.workspace_id: item
        for item in session.exec(
            select(WorkspaceMembership)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(
                WorkspaceMembership.user_id == user_id,
                Workspace.organization_id == scope.organization.id,
            )
        ).all()
    }
    if requested is not None:
        replace_ids = (
            {int(item.id) for item in session.exec(select(Workspace).where(Workspace.organization_id == scope.organization.id)).all()}
            if scope.is_organization_admin
            else set(scope.managed_workspace_ids)
        )
        for workspace_id in replace_ids:
            assignment = existing.get(workspace_id)
            desired = requested.get(workspace_id)
            if desired is None:
                if assignment is not None:
                    assignment.is_active = False
                    session.add(assignment)
                continue
            if assignment is None:
                assignment = WorkspaceMembership(workspace_id=workspace_id, user_id=user_id)
            assignment.role = desired.role
            assignment.is_active = True
            session.add(assignment)

    if update.is_active is False:
        for assignment in existing.values():
            assignment.is_active = False
            session.add(assignment)
        now = datetime.utcnow()
        for auth_session in session.exec(
            select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        ).all():
            auth_session.revoked_at = now
            session.add(auth_session)

    add_audit_event(
        session,
        organization_id=int(scope.organization.id),
        actor_user_id=scope.membership.user_id,
        action="member.updated",
        target_type="user",
        target_id=user_id,
        summary={
            "organization_role": membership.role,
            "is_active": membership.is_active,
            "workspace_ids": sorted(requested) if requested is not None else None,
        },
    )
    session.commit()
    session.refresh(membership)
    return membership
