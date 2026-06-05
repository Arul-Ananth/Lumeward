from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=100)
    hashed_password: str


class AuthIdentity(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_authidentity_provider_subject"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str = Field(index=True, max_length=64)
    subject: str = Field(max_length=255)
    email: str | None = Field(default=None, index=True, max_length=255)
    password_hash: str | None = None
    is_active: bool = Field(default=True)
    is_synthetic: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuthSession(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("token_hash", name="uq_authsession_token_hash"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    identity_id: int = Field(foreign_key="authidentity.id", index=True)
    transport: str = Field(default="bearer_session", max_length=64)
    token_hash: str = Field(max_length=64, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(index=True)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: datetime | None = None


class UserWallet(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="user.id")
    balance: int = Field(default=50)


class UsageLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    topic: str
    input_tokens: int
    output_tokens: int
    total_cost: int


class NewsletterTemplate(SQLModel, table=True):
    key: str = Field(primary_key=True, max_length=80)
    name: str = Field(max_length=120)
    description: str = Field(max_length=500)
    cadence: str = Field(default="on_demand", max_length=32)
    prompt_hint: str
    is_builtin: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NewsletterDigest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    template_key: str = Field(default="daily_tech", foreign_key="newslettertemplate.key", index=True, max_length=80)
    title: str = Field(max_length=200)
    topic: str = Field(max_length=255)
    markdown: str
    html: str
    archived: bool = Field(default=False, index=True)
    source_schedule_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class NewsletterSchedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(max_length=120)
    template_key: str = Field(foreign_key="newslettertemplate.key", index=True, max_length=80)
    topic_seed: str = Field(max_length=255)
    cadence: str = Field(max_length=16)
    local_time: str = Field(max_length=5)
    timezone: str = Field(max_length=64)
    enabled: bool = Field(default=True, index=True)
    last_run_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EventRaw(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(index=True, max_length=80)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    session_id: str = Field(index=True, max_length=64)
    payload_json: str
    hash: str = Field(index=True, max_length=64)
    source: str = Field(max_length=80)


class FilesIndex(SQLModel, table=True):
    path: str = Field(primary_key=True, max_length=512)
    content_hash: str = Field(max_length=64)
    mtime: float
    last_ingested_at: datetime | None = None
    status: str = Field(default="new", max_length=32)
    error: str | None = None


class DerivedMemory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=-1, index=True)
    memory_type: str = Field(index=True, max_length=64)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    source_refs: str
    summary_text: str
    qdrant_point_id: str = Field(max_length=64)


class FolderConsent(SQLModel, table=True):
    path: str = Field(primary_key=True, max_length=512)
    granted_at: datetime = Field(default_factory=datetime.utcnow)


class SchemaMigration(SQLModel, table=True):
    migration_id: str = Field(primary_key=True, max_length=128)
    applied_at: datetime = Field(default_factory=datetime.utcnow)
