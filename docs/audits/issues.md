# Lumeward Codebase Issue Audit

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

1. Billing still uses estimated token counts
- Evidence: `backend/server/routers/news.py` records fixed `input_tok` and `output_tok` values.
- Impact: server-mode usage logs and credit deductions are approximate.

2. "Web Search (Google)" is metadata-only
- Evidence: `backend/common/services/search/web_search.py` subclasses the generic search tool without distinct Google API behavior.
- Impact: the tool name can imply a different provider than the implementation actually uses.

3. Some compatibility modules remain intentionally
- Evidence: `backend/server/dependencies.py` and `backend/common/services/llm/crew_agent.py` are retained as compatibility shims.
- Impact: they are low-cost, but should not be used for new code.

4. Runtime data is intentionally local and ignored
- Evidence: server mode uses local SQLite and Qdrant paths when no external services are configured.
- Impact: deleting ignored local data resets local app state.
