from datetime import datetime
from typing import Any, Literal

from pydantic import EmailStr, Field, model_validator

from backend.common.models.schemas import StrictBaseModel


OrganizationRole = Literal["member", "organization_admin"]
WorkspaceRole = Literal["member", "workspace_admin"]
InvitationStatus = Literal["pending", "accepted", "revoked", "expired"]


class OrganizationSummary(StrictBaseModel):
    id: int
    name: str
    slug: str


class OrganizationSignupRequest(StrictBaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    organization_name: str = Field(min_length=1, max_length=160)


class OrganizationSignupResponse(StrictBaseModel):
    message: str
    user_id: int
    organization: OrganizationSummary
    organization_role: OrganizationRole
    session_token: str
    onboarding_required: bool = True


class AdminWorkspaceCreate(StrictBaseModel):
    name: str = Field(min_length=1, max_length=160)


class AdminWorkspaceUpdate(StrictBaseModel):
    name: str = Field(min_length=1, max_length=160)


class AdminWorkspaceResponse(StrictBaseModel):
    id: int
    organization_id: int
    name: str
    slug: str
    role: WorkspaceRole
    member_count: int = 0
    admin_count: int = 0
    created_at: datetime


class AdminBootstrapResponse(StrictBaseModel):
    organization: OrganizationSummary
    organization_role: OrganizationRole
    workspaces: list[AdminWorkspaceResponse]
    permissions: list[str]
    onboarding_required: bool


class OrganizationUpdate(StrictBaseModel):
    name: str = Field(min_length=1, max_length=160)


class WorkspaceAssignmentInput(StrictBaseModel):
    workspace_id: int
    role: WorkspaceRole = "member"


class WorkspaceAssignmentResponse(StrictBaseModel):
    workspace_id: int
    workspace_name: str
    role: WorkspaceRole


class AdminMemberResponse(StrictBaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    organization_role: OrganizationRole
    is_active: bool
    workspace_assignments: list[WorkspaceAssignmentResponse]
    created_at: datetime


class AdminMemberListResponse(StrictBaseModel):
    items: list[AdminMemberResponse]
    total: int
    page: int
    page_size: int


class AdminMemberUpdate(StrictBaseModel):
    organization_role: OrganizationRole | None = None
    is_active: bool | None = None
    workspace_assignments: list[WorkspaceAssignmentInput] | None = None

    @model_validator(mode="after")
    def require_change(self):
        if self.organization_role is None and self.is_active is None and self.workspace_assignments is None:
            raise ValueError("At least one membership change is required")
        return self


class InvitationCreate(StrictBaseModel):
    email: EmailStr
    organization_role: OrganizationRole = "member"
    workspace_assignments: list[WorkspaceAssignmentInput] = Field(default_factory=list, max_length=100)


class InvitationResponse(StrictBaseModel):
    id: int
    email: EmailStr
    organization_role: OrganizationRole
    status: InvitationStatus
    workspace_assignments: list[WorkspaceAssignmentResponse]
    expires_at: datetime
    created_at: datetime
    email_delivery_status: str
    email_delivery_error: str | None = None
    invite_url: str | None = None


class InvitationListResponse(StrictBaseModel):
    items: list[InvitationResponse]
    total: int
    page: int
    page_size: int


class InvitationInspectResponse(StrictBaseModel):
    email: EmailStr
    organization: OrganizationSummary
    organization_role: OrganizationRole
    workspace_assignments: list[WorkspaceAssignmentResponse]
    status: InvitationStatus
    expires_at: datetime
    existing_user: bool


class InvitationAccept(StrictBaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=255)

    @model_validator(mode="after")
    def complete_new_user_credentials(self):
        if (self.full_name is None) != (self.password is None):
            raise ValueError("Full name and password must be provided together")
        return self


class InvitationAcceptResponse(StrictBaseModel):
    message: str
    organization: OrganizationSummary
    session_token: str | None = None


class AdminContextItemResponse(StrictBaseModel):
    id: int
    workspace_id: int
    source: str
    content_type: str
    classification: str
    title: str
    preview: str
    tags: list[str]
    created_at: datetime


class AdminContextListResponse(StrictBaseModel):
    items: list[AdminContextItemResponse]
    total: int
    page: int
    page_size: int


class AdminTagResponse(StrictBaseModel):
    id: int
    normalized_key: str
    display_name: str
    priority: float | None = None
    blocked: bool | None = None


class AdminTagCreate(StrictBaseModel):
    display_name: str = Field(min_length=1, max_length=160)


class AuditEventResponse(StrictBaseModel):
    id: int
    actor_user_id: int | None
    actor_name: str | None
    action: str
    target_type: str
    target_id: str | None
    summary: dict[str, Any]
    created_at: datetime


class AuditListResponse(StrictBaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int


class AdminOverviewResponse(StrictBaseModel):
    member_count: int
    workspace_count: int
    pending_invitation_count: int
    shared_context_count: int
    recent_audit: list[AuditEventResponse]
