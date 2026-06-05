from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


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


class BillingReceipt(StrictBaseModel):
    deducted: int
    remaining: int | str


class NewsRequest(StrictBaseModel):
    topic: str = Field(min_length=1, max_length=255)
    serper_api_key: str | None = None
    openai_api_key: str | None = None
    template_key: str | None = Field(default=None, min_length=1, max_length=80)


class NewsResponse(StrictBaseModel):
    topic: str
    content: str
    bill: BillingReceipt


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
    created_at: str


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
    last_run_at: str | None = None
    created_at: str
    updated_at: str
