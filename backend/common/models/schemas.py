from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class UserSignup(StrictBaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=255)


class UserLogin(StrictBaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)


class AuthStatus(StrictBaseModel):
    message: str
    user_id: int | None = None
    trusted_lan_mode: bool = False
    auth_mode: str
    authenticated: bool = False
    provider: str | None = None
    requires_login: bool = True
    session_token: str | None = None


class SignupResponse(StrictBaseModel):
    message: str
    user_id: int
    auth_provider: str


class WorkspaceResponse(StrictBaseModel):
    id: int
    organization_id: int
    name: str
    slug: str
    role: str
    organization_role: str


class OrganizationCreate(StrictBaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")


class OrganizationResponse(StrictBaseModel):
    id: int
    name: str
    slug: str


class WorkspaceCreate(StrictBaseModel):
    organization_id: int
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")


class OrganizationMemberCreate(StrictBaseModel):
    email: EmailStr
    role: Literal["member", "organization_admin"] = "member"


class WorkspaceMemberCreate(StrictBaseModel):
    email: EmailStr
    role: Literal["member", "workspace_admin"] = "member"


class TagResponse(StrictBaseModel):
    id: int
    organization_id: int | None
    normalized_key: str
    display_name: str


class TagCreate(StrictBaseModel):
    organization_id: int
    display_name: str = Field(min_length=1, max_length=160)


class TagPreferenceUpdate(StrictBaseModel):
    weight: float = Field(default=1.0, ge=-1.0, le=1.0)
    muted: bool = False


class WorkspaceTagPolicyUpdate(StrictBaseModel):
    priority: float = Field(default=0.0, ge=-1.0, le=1.0)
    blocked: bool = False


class PluginManifestRequest(StrictBaseModel):
    plugin_key: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    version: str = Field(min_length=1, max_length=64)
    requested_capabilities: list[str] = Field(default_factory=list, max_length=20)
    allowed_network_origins: list[str] = Field(default_factory=list, max_length=20)
    context_types: list[str] = Field(default_factory=list, max_length=20)


class PluginInstallRequest(StrictBaseModel):
    organization_id: int
    workspace_id: int | None = None
    manifest: PluginManifestRequest


class PluginGrantRequest(StrictBaseModel):
    capability: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=512)


class PluginInstallationResponse(StrictBaseModel):
    id: int
    organization_id: int
    workspace_id: int | None
    plugin_key: str
    version: str
    status: str


class NewsRequest(StrictBaseModel):
    topic: str = Field(min_length=1, max_length=255)
    template_key: str | None = Field(default=None, min_length=1, max_length=80)
    context: str = Field(default="", max_length=10000)


class ContextIngestRequest(StrictBaseModel):
    text: str = Field(min_length=1, max_length=100000)
    source: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9._-]+$")
    title: str = Field(default="", max_length=255)
    tag_ids: list[int] = Field(default_factory=list, max_length=20)


class ContextIngestResponse(StrictBaseModel):
    chunks_indexed: int


class NewsResponse(StrictBaseModel):
    topic: str
    content: str


class FeedbackRequest(StrictBaseModel):
    original_topic: str = Field(min_length=1, max_length=255)
    feedback_text: str = Field(min_length=1, max_length=2000)
    sentiment: str = Field(min_length=1, max_length=50)


class FeedbackResponse(StrictBaseModel):
    status: str


class MessageResponse(StrictBaseModel):
    message: str


class MemoryRecord(StrictBaseModel):
    id: str
    document: str
    metadata: dict[str, Any]


class ProfileResponse(StrictBaseModel):
    memories: list[MemoryRecord]


class NewsletterTemplateResponse(StrictBaseModel):
    key: str
    name: str
    description: str
    cadence: str
    prompt_hint: str


class NewsletterSourceCapabilityResponse(StrictBaseModel):
    key: str
    display_name: str
    status: str
    supported_platforms: list[str]
    required_permissions: list[str]
    implemented: bool


class NewsletterDigestResponse(StrictBaseModel):
    id: int
    template_key: str
    title: str
    topic: str
    markdown: str
    html: str
    archived: bool
    created_at: datetime


class NewsletterScheduleCreate(StrictBaseModel):
    name: str = Field(min_length=1, max_length=120)
    template_key: str = Field(min_length=1, max_length=80)
    topic_seed: str = Field(min_length=1, max_length=255)
    cadence: str = Field(pattern="^(daily|weekly)$")
    local_time: str = Field(pattern="^([01][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field(min_length=1, max_length=64)
    enabled: bool = True


class NewsletterScheduleUpdate(StrictBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    template_key: str | None = Field(default=None, min_length=1, max_length=80)
    topic_seed: str | None = Field(default=None, min_length=1, max_length=255)
    cadence: str | None = Field(default=None, pattern="^(daily|weekly)$")
    local_time: str | None = Field(default=None, pattern="^([01][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    enabled: bool | None = None


class NewsletterScheduleResponse(StrictBaseModel):
    id: int
    name: str
    template_key: str
    topic_seed: str
    cadence: str
    local_time: str
    timezone: str
    enabled: bool
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FeedCardResponse(StrictBaseModel):
    id: int
    title: str
    bullets: list[str]
    topics: list[str]
    source_type: str
    priority_score: float
    interest_score: float
    created_at: datetime
    status: str


class FolderIngestResponse(StrictBaseModel):
    status: str
    batch_id: str
    files_seen: int
    files_ingested: int
    files_skipped: int
    files_failed: int
    message: str
