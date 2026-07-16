from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, status
from sqlmodel import Session

from backend.common.database import get_session
from backend.common.models.admin_schemas import (
    AdminBootstrapResponse,
    AdminContextItemResponse,
    AdminContextListResponse,
    AdminMemberListResponse,
    AdminMemberResponse,
    AdminMemberUpdate,
    AdminOverviewResponse,
    AdminTagCreate,
    AdminTagResponse,
    AdminWorkspaceCreate,
    AdminWorkspaceResponse,
    AdminWorkspaceUpdate,
    AuditEventResponse,
    AuditListResponse,
    InvitationCreate,
    InvitationListResponse,
    InvitationResponse,
    OrganizationSummary,
    OrganizationUpdate,
    WorkspaceAssignmentResponse,
)
from backend.common.models.schemas import (
    ContextIngestRequest,
    ContextIngestResponse,
    FolderIngestResponse,
    MessageResponse,
    WorkspaceTagPolicyUpdate,
)
from backend.common.models.sql import OrganizationMembership, User, Workspace, WorkspaceMembership
from backend.common.services.auth.resolver import get_current_principal
from backend.common.services.auth.types import AuthPrincipal
from backend.common.services.authorization import workspace_header
from backend.common.services.organization_admin import (
    _workspace_assignments_for_invitation,
    add_audit_event,
    create_admin_workspace,
    create_invitation,
    effective_invitation_status,
    get_admin_scope,
    list_admin_tags,
    list_audit_events,
    list_invitations,
    list_members,
    list_shared_context,
    overview_counts,
    rename_organization,
    rename_workspace,
    resend_invitation,
    revoke_invitation,
    update_member,
    visible_workspaces,
)
from backend.common.services.ingestion.text_context import ingest_workspace_text
from backend.common.services.tag_admin import create_admin_tag, set_admin_workspace_tag_policy


router = APIRouter(tags=["Organization Administration"])


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    detail = str(exc)
    if "not found" in detail.lower():
        raise HTTPException(status_code=404, detail=detail) from exc
    if "already" in detail.lower() or "pending invitation" in detail.lower():
        raise HTTPException(status_code=409, detail=detail) from exc
    raise HTTPException(status_code=400, detail=detail) from exc


def _scope(session: Session, principal: AuthPrincipal):
    try:
        return get_admin_scope(session, principal.user_id)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)


def _organization_summary(organization) -> OrganizationSummary:
    return OrganizationSummary(id=organization.id, name=organization.name, slug=organization.slug)


def _workspace_response(
    workspace: Workspace,
    role: str,
    member_count: int,
    admin_count: int,
) -> AdminWorkspaceResponse:
    return AdminWorkspaceResponse(
        id=workspace.id,
        organization_id=workspace.organization_id,
        name=workspace.name,
        slug=workspace.slug,
        role=role,
        member_count=member_count,
        admin_count=admin_count,
        created_at=workspace.created_at,
    )


def _permissions(scope) -> list[str]:
    if scope.is_organization_admin:
        return [
            "organization.read",
            "organization.update",
            "workspaces.read",
            "workspaces.manage",
            "members.read",
            "members.manage",
            "invitations.manage",
            "context.read",
            "tags.manage",
            "audit.read",
        ]
    return [
        "workspaces.read",
        "members.read",
        "workspace_assignments.manage",
        "context.read",
        "tags.read",
        "workspace_tag_policies.manage",
    ]


@router.get("/bootstrap", response_model=AdminBootstrapResponse)
def bootstrap(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    scope = _scope(session, principal)
    workspaces = [_workspace_response(*row) for row in visible_workspaces(session, scope)]
    return AdminBootstrapResponse(
        organization=_organization_summary(scope.organization),
        organization_role=scope.membership.role,
        workspaces=workspaces,
        permissions=_permissions(scope),
        onboarding_required=scope.is_organization_admin and not workspaces,
    )


@router.get("/overview", response_model=AdminOverviewResponse)
def overview(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        scope = _scope(session, principal)
        member_count, workspace_count, pending_count, context_count = overview_counts(session, scope)
        audit_rows, _ = list_audit_events(session, scope, page=1, page_size=5, action=None)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    recent_audit = []
    for event, actor in audit_rows:
        try:
            summary = json.loads(event.summary_json)
        except (TypeError, ValueError):
            summary = {}
        recent_audit.append(
            AuditEventResponse(
                id=event.id,
                actor_user_id=event.actor_user_id,
                actor_name=actor.full_name if actor else None,
                action=event.action,
                target_type=event.target_type,
                target_id=event.target_id,
                summary=summary,
                created_at=event.created_at,
            )
        )
    return AdminOverviewResponse(
        member_count=member_count,
        workspace_count=workspace_count,
        pending_invitation_count=pending_count,
        shared_context_count=context_count,
        recent_audit=recent_audit,
    )


@router.get("/organization", response_model=OrganizationSummary)
def get_organization(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    return _organization_summary(_scope(session, principal).organization)


@router.patch("/organization", response_model=OrganizationSummary)
def update_organization(
    request: OrganizationUpdate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        organization = rename_organization(session, _scope(session, principal), request.name)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return _organization_summary(organization)


@router.get("/workspaces", response_model=list[AdminWorkspaceResponse])
def get_workspaces(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    scope = _scope(session, principal)
    return [_workspace_response(*row) for row in visible_workspaces(session, scope)]


@router.post("/workspaces", status_code=201, response_model=AdminWorkspaceResponse)
def post_workspace(
    request: AdminWorkspaceCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        workspace = create_admin_workspace(session, _scope(session, principal), request.name)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return _workspace_response(workspace, "workspace_admin", 1, 1)


@router.patch("/workspaces/{workspace_id}", response_model=AdminWorkspaceResponse)
def patch_workspace(
    workspace_id: int,
    request: AdminWorkspaceUpdate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        scope = _scope(session, principal)
        workspace = rename_workspace(session, scope, workspace_id, request.name)
        row = next(row for row in visible_workspaces(session, scope) if row[0].id == workspace.id)
    except (PermissionError, ValueError, StopIteration) as exc:
        _raise_service_error(ValueError("Workspace not found") if isinstance(exc, StopIteration) else exc)
    return _workspace_response(*row)


def _member_response(
    membership: OrganizationMembership,
    user: User,
    assignments: list[tuple[WorkspaceMembership, Workspace]],
) -> AdminMemberResponse:
    return AdminMemberResponse(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        organization_role=membership.role,
        is_active=membership.is_active,
        workspace_assignments=[
            WorkspaceAssignmentResponse(
                workspace_id=workspace.id,
                workspace_name=workspace.name,
                role=assignment.role,
            )
            for assignment, workspace in assignments
        ],
        created_at=membership.created_at,
    )


@router.get("/members", response_model=AdminMemberListResponse)
def get_members(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    workspace_id: int | None = Depends(workspace_header),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        rows, total = list_members(
            session,
            _scope(session, principal),
            page=page,
            page_size=page_size,
            search=search,
            workspace_id=workspace_id,
        )
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return AdminMemberListResponse(
        items=[_member_response(*row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/members/{user_id}", response_model=AdminMemberResponse)
def put_member(
    user_id: int,
    request: AdminMemberUpdate,
    workspace_id: int | None = Depends(workspace_header),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        scope = _scope(session, principal)
        if not scope.is_organization_admin:
            if workspace_id is None:
                raise ValueError("X-Workspace-ID is required for workspace administration")
            if workspace_id not in scope.managed_workspace_ids:
                raise PermissionError("Workspace administration permission required")
            if request.workspace_assignments is not None and any(
                item.workspace_id != workspace_id for item in request.workspace_assignments
            ):
                raise PermissionError("Workspace administrators may update only the selected workspace")
            selected_assignments = request.workspace_assignments or []
            request = AdminMemberUpdate(workspace_assignments=selected_assignments)
            limited_scope = type(scope)(
                organization=scope.organization,
                membership=scope.membership,
                managed_workspace_ids=frozenset({workspace_id}),
            )
            update_member(session, limited_scope, user_id, request)
        else:
            update_member(session, scope, user_id, request)
        rows, _ = list_members(
            session,
            scope,
            page=1,
            page_size=100,
            search=None,
            workspace_id=None,
        )
        row = next(row for row in rows if row[1].id == user_id)
    except (PermissionError, ValueError, StopIteration) as exc:
        _raise_service_error(ValueError("Organization member not found") if isinstance(exc, StopIteration) else exc)
    return _member_response(*row)


def _invitation_response(session: Session, invitation, invite_url: str | None = None) -> InvitationResponse:
    assignments = _workspace_assignments_for_invitation(session, invitation.id)
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        organization_role=invitation.organization_role,
        status=effective_invitation_status(invitation),
        workspace_assignments=[
            WorkspaceAssignmentResponse(
                workspace_id=workspace.id,
                workspace_name=workspace.name,
                role=assignment.role,
            )
            for assignment, workspace in assignments
        ],
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        email_delivery_status=invitation.email_delivery_status,
        email_delivery_error=invitation.email_delivery_error,
        invite_url=invite_url,
    )


@router.get("/invitations", response_model=InvitationListResponse)
def get_invitations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        invitations, total = list_invitations(
            session, _scope(session, principal), page=page, page_size=page_size
        )
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return InvitationListResponse(
        items=[_invitation_response(session, item) for item in invitations],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/invitations", status_code=201, response_model=InvitationResponse)
def post_invitation(
    request: InvitationCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        invitation, url = create_invitation(session, _scope(session, principal), request)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return _invitation_response(session, invitation, url)


@router.post("/invitations/{invitation_id}/resend", response_model=InvitationResponse)
def post_resend_invitation(
    invitation_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        invitation, url = resend_invitation(session, _scope(session, principal), invitation_id)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return _invitation_response(session, invitation, url)


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invitation(
    invitation_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        revoke_invitation(session, _scope(session, principal), invitation_id)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/context", response_model=AdminContextListResponse)
def get_context(
    workspace_id: int | None = Depends(workspace_header),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    if workspace_id is None:
        raise HTTPException(status_code=400, detail="X-Workspace-ID is required")
    try:
        rows, total = list_shared_context(
            session,
            _scope(session, principal),
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
        )
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    items = []
    for item, event, tags in rows:
        payload = {}
        if event is not None:
            try:
                payload = json.loads(event.payload_json)
            except (TypeError, ValueError):
                payload = {}
        preview = str(payload.get("content") or payload.get("text") or "")[:300]
        items.append(
            AdminContextItemResponse(
                id=item.id,
                workspace_id=workspace_id,
                source=item.source,
                content_type=item.content_type,
                classification=item.classification,
                title=str(payload.get("title") or ""),
                preview=preview,
                tags=[tag.display_name for tag in tags],
                created_at=item.created_at,
            )
        )
    return AdminContextListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/context", status_code=201, response_model=ContextIngestResponse)
def post_shared_context(
    request: ContextIngestRequest,
    workspace_id: int | None = Depends(workspace_header),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    if workspace_id is None:
        raise HTTPException(status_code=400, detail="X-Workspace-ID is required")
    scope = _scope(session, principal)
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.organization_id != scope.organization.id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not scope.is_organization_admin and workspace_id not in scope.managed_workspace_ids:
        raise HTTPException(status_code=403, detail="Workspace administration permission required")
    try:
        chunks = ingest_workspace_text(
            session,
            text=request.text,
            source=request.source,
            title=request.title,
            user_id=principal.user_id,
            organization_id=scope.organization.id,
            workspace_id=workspace_id,
            tag_ids=request.tag_ids,
            commit=False,
        )
        add_audit_event(
            session,
            organization_id=scope.organization.id,
            actor_user_id=principal.user_id,
            action="shared_context.created",
            target_type="workspace",
            target_id=workspace_id,
            summary={"chunks_indexed": chunks, "source": request.source},
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ContextIngestResponse(chunks_indexed=chunks)


@router.post("/context/upload", response_model=FolderIngestResponse)
async def upload_shared_context(
    request: Request,
    file: UploadFile,
    workspace_id: int | None = Depends(workspace_header),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    if workspace_id is None:
        raise HTTPException(status_code=400, detail="X-Workspace-ID is required")
    scope = _scope(session, principal)
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.organization_id != scope.organization.id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not scope.is_organization_admin and workspace_id not in scope.managed_workspace_ids:
        raise HTTPException(status_code=403, detail="Workspace administration permission required")

    # Import locally to keep upload orchestration in one place without coupling router imports.
    from backend.server.routers.news import UploadTooLargeError, _run_bounded_ingestion

    try:
        result = await _run_bounded_ingestion(
            file,
            file.filename or "folder.zip",
            principal.user_id,
            request.headers.get("content-length"),
            organization_id=str(scope.organization.id),
            workspace_id=str(workspace_id),
            visibility="workspace",
        )
        add_audit_event(
            session,
            organization_id=scope.organization.id,
            actor_user_id=principal.user_id,
            action="shared_context.uploaded",
            target_type="workspace",
            target_id=workspace_id,
            summary={
                "files_ingested": result.files_ingested,
                "files_failed": result.files_failed,
            },
        )
        session.commit()
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.get("/tags", response_model=list[AdminTagResponse])
def get_tags(
    workspace_id: int | None = Depends(workspace_header),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        rows = list_admin_tags(session, _scope(session, principal), workspace_id)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return [
        AdminTagResponse(
            id=tag.id,
            normalized_key=tag.normalized_key,
            display_name=tag.display_name,
            priority=policy.priority if policy else None,
            blocked=policy.blocked if policy else None,
        )
        for tag, policy in rows
    ]


@router.post("/tags", status_code=201, response_model=AdminTagResponse)
def post_tag(
    request: AdminTagCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    scope = _scope(session, principal)
    if not scope.is_organization_admin:
        raise HTTPException(status_code=403, detail="Organization administration permission required")
    try:
        tag = create_admin_tag(session, scope, request.display_name)
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return AdminTagResponse(id=tag.id, normalized_key=tag.normalized_key, display_name=tag.display_name)


@router.put("/workspaces/{workspace_id}/tags/{tag_id}/policy", response_model=MessageResponse)
def put_tag_policy(
    workspace_id: int,
    tag_id: int,
    request: WorkspaceTagPolicyUpdate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    scope = _scope(session, principal)
    try:
        set_admin_workspace_tag_policy(
            session,
            scope,
            workspace_id=workspace_id,
            tag_id=tag_id,
            priority=request.priority,
            blocked=request.blocked,
        )
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    return MessageResponse(message="Workspace tag policy updated")


@router.get("/audit", response_model=AuditListResponse)
def get_audit(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    action: str | None = Query(default=None, max_length=120),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        rows, total = list_audit_events(
            session,
            _scope(session, principal),
            page=page,
            page_size=page_size,
            action=action,
        )
    except (PermissionError, ValueError) as exc:
        _raise_service_error(exc)
    items = []
    for event, actor in rows:
        try:
            summary = json.loads(event.summary_json)
        except (TypeError, ValueError):
            summary = {}
        items.append(
            AuditEventResponse(
                id=event.id,
                actor_user_id=event.actor_user_id,
                actor_name=actor.full_name if actor else None,
                action=event.action,
                target_type=event.target_type,
                target_id=event.target_id,
                summary=summary,
                created_at=event.created_at,
            )
        )
    return AuditListResponse(items=items, total=total, page=page, page_size=page_size)
