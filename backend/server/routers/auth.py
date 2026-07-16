from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from backend.common.config import AuthMode, settings
from backend.common.database import get_session
from backend.common.models.schemas import (
    AuthStatus,
    MessageResponse,
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationResponse,
    SignupResponse,
    UserLogin,
    UserSignup,
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceResponse,
    TagCreate,
    TagPreferenceUpdate,
    TagResponse,
    WorkspaceTagPolicyUpdate,
    PluginGrantRequest,
    PluginInstallRequest,
    PluginInstallationResponse,
)
from backend.common.models.admin_schemas import (
    InvitationAccept,
    InvitationAcceptResponse,
    InvitationInspectResponse,
    OrganizationSignupRequest,
    OrganizationSignupResponse,
    OrganizationSummary,
    WorkspaceAssignmentResponse,
)
from backend.common.models.sql import Organization, OrganizationMembership, User
from backend.common.services.auth.providers.interactive import login as interactive_login
from backend.common.services.auth.providers.interactive import signup as interactive_signup
from backend.common.services.auth.resolver import get_auth_context, get_current_principal
from backend.common.services.auth.store import revoke_session_token
from backend.common.services.auth.transports import extract_bearer_token
from backend.common.services.auth.types import AuthContext, AuthPrincipal
from backend.common.services.authorization import (
    add_organization_member,
    add_workspace_member,
    create_organization_for_user,
    create_workspace,
    get_workspace_memberships,
)
from backend.common.services.tags import (
    create_tag,
    list_workspace_tags,
    set_user_tag_preference,
    set_workspace_tag_policy,
)
from backend.common.services.plugins import grant_plugin_capability, install_plugin
from backend.common.services.organization_admin import (
    _workspace_assignments_for_invitation,
    accept_invitation,
    effective_invitation_status,
    invitation_by_token,
    signup_organization,
)

router = APIRouter(tags=["Auth"])


def _status_from_context(
    auth_context: AuthContext,
    *,
    message: str,
    session_token: str | None = None,
) -> AuthStatus:
    principal = auth_context.principal
    return AuthStatus(
        message=message,
        user_id=principal.user_id if principal else None,
        trusted_lan_mode=auth_context.auth_mode == AuthMode.TRUSTED_LAN.value,
        auth_mode=auth_context.auth_mode,
        authenticated=auth_context.authenticated,
        provider=auth_context.provider,
        requires_login=auth_context.auth_mode != AuthMode.TRUSTED_LAN.value,
        session_token=session_token,
    )


@router.get("/status", response_model=AuthStatus)
def get_status(auth_context: AuthContext = Depends(get_auth_context)):
    if auth_context.auth_mode == AuthMode.TRUSTED_LAN.value:
        return _status_from_context(
            auth_context,
            message="Trusted LAN mode is active.",
        )
    if auth_context.authenticated:
        return _status_from_context(auth_context, message="Authenticated session restored.")
    return _status_from_context(auth_context, message="Authentication required.")


@router.get("/workspaces", response_model=list[WorkspaceResponse])
def list_workspaces(
    auth_context: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_session),
):
    principal = auth_context.principal
    if principal is None or not auth_context.authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    return [
        WorkspaceResponse(
            id=workspace.id,
            organization_id=workspace.organization_id,
            name=workspace.name,
            slug=workspace.slug,
            role=role,
            organization_role=organization_role,
        )
        for workspace, role, organization_role in get_workspace_memberships(session, principal.user_id)
    ]


@router.post("/organizations", status_code=201, response_model=OrganizationResponse)
def create_organization(
    request: OrganizationCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    if settings.is_trusted_lan_auth():
        raise HTTPException(status_code=403, detail="Enterprise organization setup requires individual authentication")
    try:
        organization = create_organization_for_user(
            session,
            user_id=principal.user_id,
            name=request.name,
            slug=request.slug,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return organization


@router.post("/workspaces", status_code=201, response_model=WorkspaceResponse)
def create_workspace_route(
    request: WorkspaceCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        workspace = create_workspace(
            session,
            organization_id=request.organization_id,
            actor_user_id=principal.user_id,
            name=request.name,
            slug=request.slug,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WorkspaceResponse(
        id=workspace.id,
        organization_id=workspace.organization_id,
        name=workspace.name,
        slug=workspace.slug,
        role="workspace_admin",
        organization_role="organization_admin",
    )


@router.post("/organizations/{organization_id}/members", status_code=201, response_model=MessageResponse)
def add_organization_member_route(
    organization_id: int,
    request: OrganizationMemberCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        add_organization_member(
            session,
            organization_id=organization_id,
            actor_user_id=principal.user_id,
            email=request.email,
            role=request.role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(message="Organization member added")


@router.post("/workspaces/{workspace_id}/members", status_code=201, response_model=MessageResponse)
def add_workspace_member_route(
    workspace_id: int,
    request: WorkspaceMemberCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        add_workspace_member(
            session,
            workspace_id=workspace_id,
            actor_user_id=principal.user_id,
            email=request.email,
            role=request.role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(message="Workspace member added")


@router.post("/tags", status_code=201, response_model=TagResponse)
def create_tag_route(
    request: TagCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    membership = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == request.organization_id,
            OrganizationMembership.user_id == principal.user_id,
            OrganizationMembership.is_active,
            OrganizationMembership.role == "organization_admin",
        )
    ).first()
    if membership is None:
        raise HTTPException(status_code=403, detail="Organization administration permission required")
    try:
        return create_tag(session, organization_id=request.organization_id, display_name=request.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workspaces/{workspace_id}/tags", response_model=list[TagResponse])
def list_workspace_tags_route(
    workspace_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        return list_workspace_tags(session, workspace_id=workspace_id, user_id=principal.user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.put("/tags/{tag_id}/preference", response_model=MessageResponse)
def update_tag_preference_route(
    tag_id: int,
    request: TagPreferenceUpdate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        set_user_tag_preference(
            session,
            user_id=principal.user_id,
            tag_id=tag_id,
            weight=request.weight,
            muted=request.muted,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return MessageResponse(message="Tag preference updated")


@router.put("/workspaces/{workspace_id}/tags/{tag_id}/policy", response_model=MessageResponse)
def update_workspace_tag_policy_route(
    workspace_id: int,
    tag_id: int,
    request: WorkspaceTagPolicyUpdate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        set_workspace_tag_policy(
            session,
            workspace_id=workspace_id,
            actor_user_id=principal.user_id,
            tag_id=tag_id,
            priority=request.priority,
            blocked=request.blocked,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(message="Workspace tag policy updated")


@router.post("/plugins", status_code=201, response_model=PluginInstallationResponse)
def install_plugin_route(
    request: PluginInstallRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        installation = install_plugin(
            session,
            organization_id=request.organization_id,
            workspace_id=request.workspace_id,
            actor_user_id=principal.user_id,
            manifest=request.manifest,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return installation


@router.post("/plugins/{installation_id}/grants", status_code=201, response_model=MessageResponse)
def grant_plugin_capability_route(
    installation_id: int,
    request: PluginGrantRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    try:
        grant_plugin_capability(
            session,
            installation_id=installation_id,
            actor_user_id=principal.user_id,
            capability=request.capability,
            target=request.target,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(message="Plugin capability granted")


@router.post("/signup", status_code=201, response_model=SignupResponse)
def signup(user_data: UserSignup, session: Session = Depends(get_session)):
    try:
        user, identity = interactive_signup(session, user_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SignupResponse(
        message="User created",
        user_id=user.id,
        auth_provider=identity.provider,
    )


@router.post("/organization-signup", status_code=201, response_model=OrganizationSignupResponse)
def organization_signup(
    request: OrganizationSignupRequest,
    session: Session = Depends(get_session),
):
    if settings.auth_mode() != AuthMode.INTERACTIVE:
        raise HTTPException(status_code=403, detail="Organization signup requires interactive authentication")
    try:
        user, organization, raw_token = signup_organization(session, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return OrganizationSignupResponse(
        message="Organization created",
        user_id=user.id,
        organization=OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
        ),
        organization_role="organization_admin",
        session_token=raw_token,
        onboarding_required=True,
    )


@router.get("/invitations/{token}", response_model=InvitationInspectResponse)
def inspect_invitation(token: str, session: Session = Depends(get_session)):
    try:
        invitation = invitation_by_token(session, token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    organization = session.get(Organization, invitation.organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    assignments = _workspace_assignments_for_invitation(session, invitation.id)
    existing_user = session.exec(select(User).where(User.email == invitation.email)).first() is not None
    return InvitationInspectResponse(
        email=invitation.email,
        organization=OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
        ),
        organization_role=invitation.organization_role,
        workspace_assignments=[
            WorkspaceAssignmentResponse(
                workspace_id=workspace.id,
                workspace_name=workspace.name,
                role=assignment.role,
            )
            for assignment, workspace in assignments
        ],
        status=effective_invitation_status(invitation),
        expires_at=invitation.expires_at,
        existing_user=existing_user,
    )


@router.post("/invitations/{token}/accept", response_model=InvitationAcceptResponse)
def accept_organization_invitation(
    token: str,
    request: InvitationAccept,
    auth_context: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_session),
):
    try:
        invitation = invitation_by_token(session, token, for_update=True)
        organization, raw_session_token = accept_invitation(
            session,
            invitation,
            request,
            auth_context.principal if auth_context.authenticated else None,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return InvitationAcceptResponse(
        message="Invitation accepted",
        organization=OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
        ),
        session_token=raw_session_token,
    )


@router.post("/login", response_model=AuthStatus)
def login(
    user_data: UserLogin,
    auth_context: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_session),
):
    if settings.auth_mode() == AuthMode.TRUSTED_LAN:
        return _status_from_context(
            auth_context,
            message="Trusted LAN mode is enabled. Browser login is not required.",
        )

    try:
        login_context, raw_token = interactive_login(session, user_data)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return _status_from_context(
        login_context,
        message="Credentials verified.",
        session_token=raw_token,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    session: Session = Depends(get_session),
):
    if settings.auth_mode() == AuthMode.INTERACTIVE:
        token = extract_bearer_token(request)
        if token:
            revoke_session_token(session, token)
    return MessageResponse(message="Signed out")
