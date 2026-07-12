# Lumeward Roadmap and Status

## Implemented

- Local PySide desktop with SQLite, embedded Qdrant and opt-in native collectors.
- FastAPI server with PostgreSQL, external/bundled Qdrant and readiness checks.
- Interactive users plus legacy shared/trusted-LAN compatibility.
- Organizations, workspaces, memberships and request-scoped authorization.
- User, workspace and organization ownership on events and vector payloads.
- Workspace-scoped text/file/bridge ingestion from enterprise desktop clients.
- Personal tag preferences and workspace tag policies.
- Plugin installation metadata and independently scoped capability grants.
- Typed generation entry point, consolidated document ingestion and scoped retrieval.
- Newsletter templates, history, schedules, feed cards and deep dives.
- Native Qdrant companion-process lifecycle and enterprise packaging guidance.
- Standard `pyproject.toml`/`uv.lock` workflow with desktop, development and packaging extras.

## Next important work

- Complete organization-member administration and end-user team onboarding.
- Replace development self-signup with OIDC/enterprise provisioning.
- Add an administration surface for memberships, tags and plugin grants.
- Add compliant deletion, retention enforcement, audit records and export workflows.
- Add signed server/desktop installers, SBOMs and release CI for target platforms.
- Add live PostgreSQL/Qdrant isolation and upgrade tests.

## Deferred

- Plugin execution, plugin credential storage and plugin-driven ingestion.
- Isolated connector workers and independently enforced network/filesystem capabilities.
- Full public-internet deployment profile.
- Richer desktop accessibility and visual polish.
- Removal of remaining legacy auth aliases and transitional service wrappers.

Deferred items are not release commitments.
