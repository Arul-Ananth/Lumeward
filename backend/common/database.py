"""Mode-aware relational database runtime."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import Lock

from sqlalchemy import Connection, Engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

from backend.common.config import AppMode, settings
from backend.common.models.sql import AuthIdentity, DerivedMemory, EventRaw, SchemaMigration

_engine: Engine | None = None
_session_factory: sessionmaker | None = None
_runtime_lock = Lock()
DesktopMigration = tuple[str, Callable[[Connection], None]]


def _build_engine() -> Engine:
    database_url = settings.database_url()
    common_options = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            **common_options,
        )
    return create_engine(
        database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        **common_options,
    )


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        with _runtime_lock:
            if _engine is None:
                _engine = _build_engine()
                _session_factory = sessionmaker(bind=_engine, class_=Session, expire_on_commit=False)
    return _engine


def get_session_factory() -> sessionmaker:
    get_engine()
    assert _session_factory is not None
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    with session_scope() as session:
        yield session


def create_db_and_tables() -> None:
    """Create missing tables for the active runtime.

    Existing server tables are intentionally not altered here; database changes
    are an operational/DBA concern rather than an application version gate.
    """
    engine = get_engine()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if settings.APP_MODE == AppMode.SERVER:
        SQLModel.metadata.create_all(engine, tables=server_schema_tables())
        _reconcile_server_schema(engine)
    else:
        SQLModel.metadata.create_all(engine)
    if settings.APP_MODE == AppMode.DESKTOP:
        _run_desktop_migrations(engine)


def _reconcile_server_schema(engine: Engine) -> None:
    """Apply the small, idempotent compatibility delta needed by existing PostgreSQL databases."""
    if engine.dialect.name != "postgresql":
        return
    statements = (
        "ALTER TABLE eventraw ADD COLUMN IF NOT EXISTS organization_id VARCHAR(128)",
        "ALTER TABLE eventraw ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(128)",
        'ALTER TABLE eventraw ADD COLUMN IF NOT EXISTS owner_user_id INTEGER REFERENCES "user"(id)',
        "ALTER TABLE eventraw ADD COLUMN IF NOT EXISTS visibility VARCHAR(32) NOT NULL DEFAULT 'private'",
        "CREATE INDEX IF NOT EXISTS ix_eventraw_organization_id ON eventraw (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_eventraw_workspace_id ON eventraw (workspace_id)",
        "CREATE INDEX IF NOT EXISTS ix_eventraw_owner_user_id ON eventraw (owner_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_eventraw_visibility ON eventraw (visibility)",
        "CREATE INDEX IF NOT EXISTS ix_eventraw_owner_visibility ON eventraw (owner_user_id, visibility, ts)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_org_membership_one_active_per_user "
        "ON organizationmembership (user_id) WHERE is_active",
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _migration_001_add_derivedmemory_user_id(connection: Connection) -> None:
    table_name = getattr(DerivedMemory, "__tablename__", "derivedmemory")
    columns = connection.exec_driver_sql(f"PRAGMA table_info('{table_name}')").fetchall()
    column_names = {row[1] for row in columns}
    if "user_id" not in column_names:
        connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER DEFAULT -1")
        connection.exec_driver_sql(f"UPDATE {table_name} SET user_id = -1 WHERE user_id IS NULL")
    connection.exec_driver_sql(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_user_id ON {table_name}(user_id)")


def _migration_002_backfill_auth_identities(connection: Connection) -> None:
    identity_table = getattr(AuthIdentity, "__tablename__", "authidentity")
    connection.exec_driver_sql(
        f"""
        INSERT INTO {identity_table}
        (user_id, provider, subject, email, password_hash, is_active, is_synthetic, created_at, updated_at)
        SELECT u.id, 'interactive_password', lower(u.email), u.email, u.hashed_password, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM user AS u
        LEFT JOIN {identity_table} AS ai
            ON ai.user_id = u.id AND ai.provider = 'interactive_password'
        WHERE ai.id IS NULL
        """
    )


def _migration_003_newsletter_curation_tables(connection: Connection) -> None:
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_newsletterdigest_user_archived_created "
        "ON newsletterdigest(user_id, archived, created_at)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_newsletterschedule_user_enabled_time "
        "ON newsletterschedule(user_id, enabled, local_time)"
    )


def _migration_004_intelligence_feed(connection: Connection) -> None:
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_intelligencefeed_user_status_priority "
        "ON intelligencefeed(user_id, status, priority_score, created_at)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_intelligencefeed_user_source_ref "
        "ON intelligencefeed(user_id, source_ref)"
    )


def _migration_005_event_ownership(connection: Connection) -> None:
    table_name = getattr(EventRaw, "__tablename__", "eventraw")
    columns = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info('{table_name}')").fetchall()}
    additions = {
        "organization_id": "VARCHAR(128)",
        "workspace_id": "VARCHAR(128)",
        "owner_user_id": "INTEGER",
        "visibility": "VARCHAR(32) NOT NULL DEFAULT 'private'",
    }
    for column, definition in additions.items():
        if column not in columns:
            connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}")
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_eventraw_owner_visibility "
        f"ON {table_name}(owner_user_id, visibility, ts)"
    )


DESKTOP_MIGRATIONS: list[DesktopMigration] = [
    ("001_add_derivedmemory_user_id", _migration_001_add_derivedmemory_user_id),
    ("002_backfill_auth_identities", _migration_002_backfill_auth_identities),
    ("003_newsletter_curation_tables", _migration_003_newsletter_curation_tables),
    ("004_intelligence_feed", _migration_004_intelligence_feed),
    ("005_event_ownership", _migration_005_event_ownership),
]


def _run_desktop_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    SchemaMigration.__table__.create(bind=engine, checkfirst=True)
    with engine.begin() as connection:
        applied = {
            row[0]
            for row in connection.execute(text(f"SELECT migration_id FROM {SchemaMigration.__tablename__}")).fetchall()
        }
        for migration_id, migration_fn in DESKTOP_MIGRATIONS:
            if migration_id in applied:
                continue
            migration_fn(connection)
            connection.execute(
                text(
                    f"INSERT INTO {SchemaMigration.__tablename__} "
                    "(migration_id, applied_at) VALUES (:migration_id, CURRENT_TIMESTAMP)"
                ),
                {"migration_id": migration_id},
            )


def check_database_ready() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


def server_schema_tables():
    return [
        table
        for table in SQLModel.metadata.sorted_tables
        if not table.info.get("desktop_only", False)
    ]


def dispose_database() -> None:
    global _engine, _session_factory
    with _runtime_lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _session_factory = None


def reset_database_runtime() -> None:
    """Reset cached clients after tests or explicit runtime-mode changes."""
    dispose_database()
