"""Explicit pre-release PostgreSQL schema management."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from sqlalchemy import inspect
from sqlalchemy.engine import make_url
from sqlmodel import SQLModel

from backend.common.config import AppMode, settings
from backend.common.database import (
    SERVER_SCHEMA_VERSION,
    check_database_ready,
    check_server_schema_ready,
    dispose_database,
    get_engine,
    server_schema_tables,
    session_scope,
)
from backend.common.models.sql import ApplicationSchema
from backend.common.services.memory import vector_db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the disposable pre-release server schema.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Check PostgreSQL connectivity and schema version.")
    subparsers.add_parser("initialize", help="Create tables in an empty PostgreSQL database.")
    for command in ("refresh", "refresh-all"):
        command_parser = subparsers.add_parser(command, help=f"Destructively run {command}.")
        command_parser.add_argument(
            "--confirm",
            required=True,
            help="Exact configured database name; required to confirm permanent data deletion.",
        )
    return parser


def _require_server_mode() -> None:
    if settings.APP_MODE != AppMode.SERVER:
        raise RuntimeError("Set APP_MODE=SERVER before managing the PostgreSQL schema.")
    settings.validate_storage_configuration()


def _database_name() -> str:
    return make_url(settings.DATABASE_URL).database or ""


def _require_confirmation(value: str) -> None:
    expected = _database_name()
    if not expected or value != expected:
        raise RuntimeError(f"Confirmation must exactly match the configured database name: {expected!r}")


def status() -> None:
    check_database_ready()
    tables = set(inspect(get_engine()).get_table_names())
    if ApplicationSchema.__tablename__ not in tables:
        print(f"PostgreSQL connection: OK ({_database_name()})")
        print("Schema: NOT INITIALIZED")
        return
    check_server_schema_ready()
    print(f"PostgreSQL connection: OK ({_database_name()})")
    print(f"Schema: READY (version {SERVER_SCHEMA_VERSION})")


def initialize() -> None:
    engine = get_engine()
    existing = set(inspect(engine).get_table_names())
    application_tables = {table.name for table in server_schema_tables()}
    conflicting = existing & application_tables
    if conflicting:
        raise RuntimeError(
            "Application tables already exist; initialize only supports an empty schema. "
            "Use refresh with explicit confirmation."
        )
    SQLModel.metadata.create_all(engine, tables=server_schema_tables())
    _write_schema_version()
    print(f"Initialized PostgreSQL schema version {SERVER_SCHEMA_VERSION} in {_database_name()!r}.")


def refresh(*, include_qdrant: bool) -> None:
    engine = get_engine()
    tables = server_schema_tables()
    SQLModel.metadata.drop_all(engine, tables=tables)
    SQLModel.metadata.create_all(engine, tables=tables)
    _write_schema_version()
    print(f"Recreated PostgreSQL schema version {SERVER_SCHEMA_VERSION} in {_database_name()!r}.")
    if include_qdrant:
        _refresh_qdrant()
        print("Recreated Lumeward Qdrant collections.")


def _write_schema_version() -> None:
    with session_scope() as session:
        session.add(ApplicationSchema(id=1, version=SERVER_SCHEMA_VERSION))
        session.commit()


def _refresh_qdrant() -> None:
    vector_db.close_qdrant()
    client = vector_db.get_client()
    for collection in (
        settings.QDRANT_COLLECTION_USER_DOCS,
        settings.QDRANT_COLLECTION_SESSION_MEMORY,
        settings.QDRANT_COLLECTION_USER_PROFILE,
    ):
        if client.collection_exists(collection):
            client.delete_collection(collection)
    vector_db.initialize_qdrant_collections()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _require_server_mode()
        if args.command == "status":
            status()
        elif args.command == "initialize":
            initialize()
        else:
            _require_confirmation(args.confirm)
            refresh(include_qdrant=args.command == "refresh-all")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        vector_db.close_qdrant()
        dispose_database()


if __name__ == "__main__":
    raise SystemExit(main())
