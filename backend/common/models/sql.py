from datetime import datetime
from typing import Optional

from sqlalchemy import Index, Text, UniqueConstraint
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


class NewsletterTemplate(SQLModel, table=True):
    key: str = Field(primary_key=True, max_length=80)
    name: str = Field(max_length=120)
    description: str = Field(max_length=500)
    cadence: str = Field(default="on_demand", max_length=32)
    prompt_hint: str = Field(sa_type=Text)
    is_builtin: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NewsletterDigest(SQLModel, table=True):
    __table_args__ = (
        Index("ix_newsletterdigest_user_archived_created", "user_id", "archived", "created_at"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    template_key: str = Field(default="daily_tech", foreign_key="newslettertemplate.key", index=True, max_length=80)
    title: str = Field(max_length=200)
    topic: str = Field(max_length=255)
    markdown: str = Field(sa_type=Text)
    html: str = Field(sa_type=Text)
    archived: bool = Field(default=False, index=True)
    source_schedule_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class NewsletterSchedule(SQLModel, table=True):
    __table_args__ = (
        Index("ix_newsletterschedule_user_enabled_time", "user_id", "enabled", "local_time"),
    )
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


class IntelligenceFeed(SQLModel, table=True):
    __table_args__ = (
        Index("ix_intelligencefeed_user_status_priority", "user_id", "status", "priority_score", "created_at"),
        Index("ix_intelligencefeed_user_source_ref", "user_id", "source_ref"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=200)
    summary_json: str = Field(sa_type=Text)
    source_type: str = Field(max_length=80, index=True)
    source_ref: str = Field(max_length=512, index=True)
    topic_key: str = Field(max_length=120, index=True)
    topics_json: str = Field(sa_type=Text)
    interest_score: float = Field(default=0.0, index=True)
    priority_score: float = Field(default=0.0, index=True)
    status: str = Field(default="new", max_length=32, index=True)
    raw_event_ids_json: str = Field(sa_type=Text)
    deep_dive_digest_id: int | None = Field(default=None, foreign_key="newsletterdigest.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    dismissed_at: datetime | None = Field(default=None, index=True)
    failure_reason: str | None = Field(default=None, sa_type=Text)


class EventRaw(SQLModel, table=True):
    __table_args__ = (
        Index("ix_eventraw_session_ts", "session_id", "ts"),
        Index("ix_eventraw_hash_ts", "hash", "ts"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(index=True, max_length=80)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    session_id: str = Field(index=True, max_length=64)
    payload_json: str = Field(sa_type=Text)
    hash: str = Field(index=True, max_length=64)
    source: str = Field(max_length=80)


class FilesIndex(SQLModel, table=True):
    path: str = Field(primary_key=True, max_length=512)
    content_hash: str = Field(max_length=64)
    mtime: float
    last_ingested_at: datetime | None = None
    status: str = Field(default="new", max_length=32)
    error: str | None = Field(default=None, sa_type=Text)


class DerivedMemory(SQLModel, table=True):
    __table_args__ = (
        Index("ix_derivedmemory_user_type_ts", "user_id", "memory_type", "ts"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=-1, index=True)
    memory_type: str = Field(index=True, max_length=64)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    source_refs: str = Field(sa_type=Text)
    summary_text: str = Field(sa_type=Text)
    qdrant_point_id: str = Field(max_length=64)


class FolderConsent(SQLModel, table=True):
    path: str = Field(primary_key=True, max_length=512)
    granted_at: datetime = Field(default_factory=datetime.utcnow)


class SchemaMigration(SQLModel, table=True):
    __table_args__ = {"info": {"desktop_only": True}}
    migration_id: str = Field(primary_key=True, max_length=128)
    applied_at: datetime = Field(default_factory=datetime.utcnow)


class ApplicationSchema(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    version: int
    updated_at: datetime = Field(default_factory=datetime.utcnow)
