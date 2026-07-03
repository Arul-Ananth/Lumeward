# Architecture Overview

## Runtime Modes

- Current release target: `1.0.0-beta.1`.
- `SERVER` mode runs FastAPI for web clients.
- `DESKTOP` mode runs PySide6 + qasync with a local bridge and background telemetry runtime.
- Runtime resolution is centralized in `backend/main.py` and follows:
  - CLI flags
  - environment variables
  - code defaults

## Current Implemented Architecture

### Backend core

- `backend/common/config.py`
  - shared settings, mode/auth resolution, desktop data-dir selection
- `backend/common/database.py`
  - mode-aware SQLModel engine/session setup, PostgreSQL pooling, desktop
    compatibility migrations, and server schema-version validation
- `backend/common/services/`
  - `auth/` web identity/session helpers
  - `newsletter/` active newsletter curation pipeline, templates, compiler, history persistence
  - `llm/` provider factory, tool policy, CrewAI builders, and compatibility wrappers
  - `memory/` vector and clipboard-history retrieval helpers
  - `ingestion/` server folder upload staging, safe zip extraction, file indexing, and restart cleanup
  - `search/` Serper and desktop fallback search
  - `telemetry/` consent, ingestion, workers, session/profile rollups

### Server mode

- App factory lives in `backend/server/app.py`.
- PostgreSQL is required through `DATABASE_URL`; schema changes are managed
  explicitly with `scripts/dev/database.py`.
- Qdrant is required through `QDRANT_URL`; localhost services are supported.
- `/health/live` and `/health/ready` expose process and dependency readiness.
- Web auth supports `trusted_lan` and `interactive` modes.
- Remote OpenAI-compatible engine support is optional and stays behind the backend.
- Remote engine mode sends only sanitized model-generation payloads to `ENGINE_BASE_URL`; auth, memory, telemetry, schedules, digest history, and vector storage stay on the Lumeward host.
- Server mode supports explicit `.zip` folder upload at `POST /news/ingest/folder`.
- Uploaded archives and extracted files are staged under `DATA_DIR / FOLDER_UPLOAD_DIR`.
- Staged upload files are deleted only on server startup when `FOLDER_UPLOAD_DELETE_ON_RESTART=true`.
- Compressed and expanded upload limits are configured with
  `FOLDER_UPLOAD_MAX_ARCHIVE_MB` and `FOLDER_UPLOAD_MAX_EXPANDED_MB`; the
  defaults are 250 MB and 1000 MB.
- Indexed PostgreSQL/Qdrant state remains after staged upload files are cleaned up.

### Desktop mode

- Desktop entrypoint lives in `backend/desktop/main.py`.
- Desktop storage remains SQLite plus embedded Qdrant and ignores server URLs.
- Desktop startup now applies saved theme preference before showing the main window.
- The main desktop UI is organized around a `Personal Feed`, a collapsible `Guidance` control, and a `Deep Dive Viewer`.
- The desktop UI is scrollable at the page level and keeps execution logs collapsed by default.
- Desktop settings now group:
  - appearance
  - API keys
  - ingestion
  - privacy

### Search and current-date behavior

- Search mode resolves to `serper`, `fallback`, or `disabled`.
- Desktop fallback search uses `ddgs` plus extraction.
- Server fallback search is disabled unless `ALLOW_SERVER_DDG_FALLBACK=true` is explicitly set.
- Time-sensitive prompts are grounded to runtime date context.
- Clipboard-history prompts use a direct recent-clipboard path before falling back to semantic memory.

### Newsletter curation

- `backend/common/services/newsletter/pipeline.py` is the active orchestration entry point.
- `templates.py` owns built-in newsletter templates.
- `compiler.py` converts generated content into Markdown and minimal safe HTML.
- `backend/common/services/llm/newsletter_service.py` is a compatibility wrapper only.
- SQLModel persistence covers templates, generated digests, and schedules.
- `/news/generate` remains compatible with the frontend and persists generated digests.
- `/news/history`, `/news/templates`, `/news/schedules`, `/news/feed`, and `/news/ingest/folder` expose the current server surface.
- `/news/sources` exposes metadata-only placeholders for future source integrations in Beta 1.0; no plugin execution or ingestion is active.

### Desktop bridge

- The bridge is loopback-only and token-protected.
- It prefers port `12345`, then falls back to an OS-assigned port.
- Uvicorn lifespan is disabled for the bridge app to prevent shutdown noise.

## Service Layer Conventions

- Keep orchestration modules thin and composable.
- Keep newsletter orchestration under `services/newsletter/`.
- Keep provider-specific logic isolated under `services/llm/`.
- Keep storage/memory code isolated under `services/memory/`.
- Keep reusable upload and file-ingestion code isolated under `services/ingestion/`.
- Keep external network tools isolated under `services/search/`.
- Use compatibility wrappers in `services/*.py` only for transition/import stability.

## Scripts and Docs

- `scripts/verify/` automated verification checks only
- `scripts/manual/` manual diagnostics
- `scripts/dev/` operational/developer scripts
- `docs/security.md` trust boundaries and safeguards
- `modes.md` runtime/trust profile documentation
- `docs/roadmap.md` implemented work and optional future directions

## Possible Future Directions

These are not commitments unless explicitly scheduled:

- stronger public-internet deployment hardening
- per-user memory isolation across all web modes
- richer desktop visual polish beyond the current structure/theme work
- a dedicated remote job/code-execution engine separated from the LLM provider path
- deeper response typing for profile and API payloads
- further pruning of legacy compatibility wrappers after import migration finishes
