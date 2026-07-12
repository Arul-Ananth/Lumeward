# Schema Management Strategy

Lumeward intentionally uses separate schema policies for desktop and server
storage during the pre-release phase.

## Desktop

- SQLite remains self-initializing through `SQLModel.metadata.create_all()`.
- `SchemaMigration` records the small ordered compatibility migrations needed
  to preserve existing desktop installations.
- Desktop startup never reads `DATABASE_URL` or uses the server database.

## Server

- PostgreSQL databases and roles are created by an administrator.
- Application startup creates missing tables, reconciles the event-ownership columns without schema versioning, and checks connectivity.
  it never creates, drops, or upgrades tables.
- `python scripts/dev/database.py initialize` creates an empty schema.
- `status` reports connectivity and schema readiness.
- `refresh --confirm <database>` deletes and recreates PostgreSQL application
  tables.
- `refresh-all --confirm <database>` also recreates Lumeward Qdrant collections.

This reset-oriented policy is acceptable only while server data is disposable.
Formal versioned migrations must be introduced before production data needs to
survive schema changes.
