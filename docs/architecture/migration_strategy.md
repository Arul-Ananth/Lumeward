# Schema Management Strategy

Lumeward does not use a server schema-version table.

## Desktop

SQLite is initialized with `SQLModel.metadata.create_all()`. A small local
`SchemaMigration` ledger preserves existing desktop databases through ordered,
idempotent compatibility changes. It is local migration history, not an
application or server schema version.

## Server

- An administrator creates the PostgreSQL database and role.
- Startup creates missing application tables.
- Startup idempotently adds the `EventRaw` organization, workspace, owner and
  visibility columns and related indexes when upgrading an older database.
- Startup never creates or drops the PostgreSQL database.
- The compatibility reconciliation is deliberately limited; future structural
  changes require an explicit operational change rather than a version gate.

`scripts/dev/database.py` offers connectivity/status checks, empty-schema
initialization and explicitly confirmed destructive refreshes for disposable
development environments. Refresh is not part of normal startup and must not be
used against production data.
