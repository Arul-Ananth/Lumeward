"""Shared database setup."""
from collections.abc import Callable

from sqlmodel import Session, SQLModel, create_engine

from backend.common.config import settings
from backend.common.models.sql import AuthIdentity, DerivedMemory, SchemaMigration

sqlite_file_name = "lumeward.db"
sqlite_url = f"sqlite:///{settings.DATA_DIR / sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

Migration = tuple[str, Callable]


def _ensure_migration_table() -> None:
    SchemaMigration.__table__.create(bind=engine, checkfirst=True)


def _migration_001_add_derivedmemory_user_id(conn) -> None:
    if engine.dialect.name != "sqlite":
        return

    table_name = getattr(DerivedMemory, "__tablename__", "derivedmemory")
    columns = conn.exec_driver_sql(f"PRAGMA table_info('{table_name}')").fetchall()
    column_names = {row[1] for row in columns}
    if "user_id" not in column_names:
        conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER DEFAULT -1")
        conn.exec_driver_sql(f"UPDATE {table_name} SET user_id = -1 WHERE user_id IS NULL")
    conn.exec_driver_sql(
        f"CREATE INDEX IF NOT EXISTS ix_{table_name}_user_id ON {table_name}(user_id)"
    )


def _migration_002_backfill_auth_identities(conn) -> None:
    identity_table = getattr(AuthIdentity, "__tablename__", "authidentity")
    conn.exec_driver_sql(
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


def _migration_003_newsletter_curation_tables(conn) -> None:
    if engine.dialect.name != "sqlite":
        return
    conn.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_newsletterdigest_user_archived_created
        ON newsletterdigest(user_id, archived, created_at)
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_newsletterschedule_user_enabled_time
        ON newsletterschedule(user_id, enabled, local_time)
        """
    )
    conn.exec_driver_sql(
        """
        INSERT INTO userwallet (user_id, balance)
        SELECT u.id, 50
        FROM user AS u
        LEFT JOIN userwallet AS uw ON uw.user_id = u.id
        WHERE uw.user_id IS NULL
        """
    )


MIGRATIONS: list[Migration] = [
    ("001_add_derivedmemory_user_id", _migration_001_add_derivedmemory_user_id),
    ("002_backfill_auth_identities", _migration_002_backfill_auth_identities),
    ("003_newsletter_curation_tables", _migration_003_newsletter_curation_tables),
]


def _run_migrations() -> None:
    _ensure_migration_table()
    with engine.begin() as conn:
        applied = {
            row[0]
            for row in conn.exec_driver_sql(
                f"SELECT migration_id FROM {SchemaMigration.__tablename__}"
            ).fetchall()
        }
        for migration_id, migration_fn in MIGRATIONS:
            if migration_id in applied:
                continue
            migration_fn(conn)
            conn.exec_driver_sql(
                f"INSERT INTO {SchemaMigration.__tablename__} (migration_id, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
                (migration_id,),
            )


def create_db_and_tables() -> None:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _run_migrations()


def get_session():
    with Session(engine) as session:
        yield session
