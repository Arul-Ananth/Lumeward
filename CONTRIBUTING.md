# Contributing Guidelines

## Goals

- Keep behavior correct, code readable, and boundaries clear.
- Prefer explicit, small modules over large mixed-responsibility files.

## Folder Conventions

- Backend service domains:
  - `backend/common/services/auth`
  - `backend/common/services/llm`
  - `backend/common/services/memory`
  - `backend/common/services/search`
  - `backend/common/services/telemetry`
- Transition wrappers under `backend/common/services/*.py` should remain thin re-exports.
- Docs go under `docs/` by category (`architecture`, `audits`, `prompts`, `samples`).
- Operational scripts go under `scripts/dev/`.

## Naming

- Python modules: `snake_case.py`
- React pages/components: `PascalCase.tsx`
- Keep filename and exported symbol aligned (`Dashboard.tsx` exports `Dashboard`).

## Import Rules

- Prefer domain imports, for example:
  - `from backend.common.services.llm.newsletter_service import newsletter_service`
  - `from backend.common.services.memory.vector_db import get_memory_context`
- Avoid introducing new imports from legacy wrapper modules unless required for compatibility.

## Editing Rules

- Keep comments short and purposeful.
- Do not combine refactors with unrelated behavior changes.
- Add/update docs when moving files or changing public module paths.

## Verification

- Backend compile check: `python -m compileall backend`
- Frontend build check: `npm run build` (in `frontend/`)
- Run targeted scripts in `scripts/verify/` for affected areas.
- Storage changes must run `verify_desktop_database_upgrade.py`,
  `verify_manual_database_management.py`, `verify_storage_modes.py`, and the
  relevant Qdrant verification scripts.
- Server schema commands live in `scripts/dev/database.py`; destructive refresh
  must always require exact database-name confirmation.
