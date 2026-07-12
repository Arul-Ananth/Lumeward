# Lumeward Codebase Issue Audit

> Historical audit snapshot. See `../architecture/overview.md` and
> `../roadmap.md` for current implementation status.

Date: 2026-06-04
Scope: Static review of backend, desktop, frontend, docs, packaging metadata, and local ignored artifacts.
Checks run during cleanup:
- `python -m compileall backend scripts`
- `npm.cmd run build` in `frontend/`

## Resolved In Cleanup

1. Packaging spec was present locally but ignored
- Evidence: `.gitignore` ignored `*.spec`, while project docs reference `packaging/pyinstaller/Lumeward.spec`.
- Resolution: the PyInstaller spec is explicitly unignored so it can be tracked.

2. Frontend lockfile was present locally but ignored
- Evidence: `.gitignore` ignored `package-lock.json`, while `frontend/package-lock.json` exists.
- Resolution: the frontend lockfile is explicitly unignored so installs are reproducible.

3. Dashboard page casing differed between Git and the filesystem
- Evidence: Git tracked `frontend/src/pages/DashBoard.tsx`, while imports and the filesystem use `Dashboard.tsx`.
- Resolution: the Git-tracked path is normalized to `frontend/src/pages/Dashboard.tsx`.

4. Stale audit findings conflicted with current implementation
- Evidence: the previous audit claimed frontend build and CLI mode overrides were broken.
- Resolution: those claims were removed because current code builds and `backend/main.py` implements CLI startup overrides.

## Remaining Follow-Up Items

1. "Web Search (Google)" is metadata-only
- Evidence: `backend/common/services/search/web_search.py` subclasses the generic search tool without distinct Google API behavior.
- Impact: the tool name can imply a different provider than the implementation actually uses.

2. Runtime storage is mode-specific
- Evidence: desktop mode uses ignored local SQLite/embedded-Qdrant data; server
  mode requires PostgreSQL and a configured Qdrant service.
- Impact: desktop data remains local, while server deployments must provision
  and explicitly initialize their storage dependencies.
