# Lumeward: Historical Capability Audit with Privacy and Security

Date: 2026-03-16  
Scope: Historical repository implementation review + external security pattern mapping + Python dependency standards audit.

Status: archived reference. This document is not the active Lumeward architecture plan. Active newsletter orchestration lives under `backend/common/services/newsletter/`, and Lumeward no longer uses a generic OpenClaw-style action execution surface as an active design target.

## 1) Current Lumeward Functionality (Implementation-Aligned)

### 1.1 Runtime modes
- Server mode (`backend/main.py`):
  - Starts FastAPI with `/auth` and `/news` routers.
  - Uses env-driven bind host/port (`SERVER_HOST`, `SERVER_PORT`).
  - Uses env-driven CORS allowlist (`CORS_ALLOWED_ORIGINS` via `settings.cors_origins()`).
- Desktop mode (`backend/desktop/main.py`):
  - Starts PySide6 UI with qasync event loop.
  - Provisions local desktop user account and wallet.
  - Starts local bridge API in separate process (`backend/desktop/services/api_server.py`) on loopback.
  - Enables optional OCR/snipping, file ingestion, and telemetry workers.

### 1.2 Auth and API
- Auth routes (`backend/server/routers/auth.py`):
  - `/auth/signup`, `/auth/login` retained for future auth work.
- Protected routes (`backend/server/routers/news.py`):
  - `/news/generate`, `/news/feedback`, `/news/profile`, `/news/profile/{user_id}`.
  - In trusted LAN mode, dependency resolves a fixed trusted server user instead of JWT auth.

### 1.3 LLM and newsletter flow
- Newsletter generation (`backend/common/services/newsletter/pipeline.py`):
  - CrewAI researcher + writer tasks.
  - Supports provider switch through `LLM_PROVIDER` (`ollama`, `openai`, `google`).
  - Uses user context from vector memory (`vector_db.get_memory_context`).
  - Sanitizes memory context (`memory_sanitizer.py`) before prompt injection.

### 1.4 Search tooling
- Web search tool (`backend/common/services/search/web_search.py`):
  - Primary: Serper search endpoint.
  - Desktop fallback: DDG + trafilatura extraction.
  - Registered tool names: `Web Search`, `Web Search (Google)` (currently shared behavior class).

### 1.5 Memory and vector layer
- Vector storage (`backend/common/services/memory/vector_db.py`):
  - Qdrant collections for profile/session/docs.
  - User filter enforced in payload queries.
  - Feedback persisted to profile collection with sentiment/topic metadata.

### 1.6 Desktop telemetry and ingestion
- Manager (`backend/desktop/telemetry_manager.py`):
  - Runs dispatcher/ingestion/summary workers in dedicated runtime thread.
  - Handles startup, emission, queue drain, and shutdown.
- Collectors:
  - Clipboard (opt-in).
  - File drag-drop and folder watch (with consent).
  - Output read-time/scroll/copy telemetry.
- Ingestion pipeline (`backend/common/services/telemetry/workers.py` + `ingestion.py`):
  - Text extraction for `.txt/.md/.html/.pdf/.docx`.
  - Chunking + embeddings + Qdrant upsert.
  - Session summary -> derived memory -> optional profile rollup.

### 1.7 Frontend
- React + Vite + MUI with API wrapper (`frontend/src/services/api.ts`).
- API base URL is env-driven (`VITE_API_BASE_URL`) with localhost fallback.
- Active LAN flow goes directly to the dashboard without browser auth.

## 2) Historical External-Pattern Recommendations (Privacy/Security-First)

This section is retained as historical input only. Current Lumeward focuses on privacy-first newsletter curation, not a generic agent/action runtime.

### 2.1 Adopt an explicit zero-trust agent execution model (P0)
- Treat agent tool execution as untrusted workload.
- Introduce policy-enforced tool runtime boundaries:
  - Filesystem scope (workspace-only or deny by default).
  - Network egress scope (allowlist only, DNS/IP restrictions).
  - Process/system call restrictions per tool class.
- Implement per-task execution policy object resolved before tool run.

Suggested code area:
- `backend/common/services/newsletter/pipeline.py` (tool invocation path)
- `backend/common/services/search/web_search.py` (network-bound tool runner)

### 2.2 Add hardened remote-access pattern (P0)
- Keep default bind local-only.
- For remote use:
  - Strict `CORS_ALLOWED_ORIGINS` allowlist.
  - Authenticated gateway mode (reverse proxy + TLS + token/session control).
  - Never expose desktop bridge directly; keep loopback-only bridge with per-session secret token.

Suggested code area:
- `backend/main.py`, `.env.example`, deployment docs
- `backend/desktop/services/api_server.py` (ingest auth token)

### 2.3 Enforce user-consent policy gates for data capture (P0)
- Clipboard is now opt-in in desktop settings. Extend same policy to all sensitive capture:
  - Explicit consent flags per collector type.
  - Per-collector retention windows.
  - Data minimization mode (store hashes/summaries instead of raw text for clipboard by default).

Suggested code area:
- `backend/desktop/preferences.py`
- `backend/desktop/collectors/clipboard_collector.py`
- `backend/common/services/telemetry/workers.py`

### 2.4 Add auditable policy decisions (P1)
- Log policy decisions in structured form:
  - tool, scope, request, allow/deny reason, user/session id.
- Persist immutable audit stream for incident investigation.

### 2.5 Add prompt/tool safety controls (P1)
- Current sanitizer removes common instruction patterns but is heuristic.
- Upgrade to layered controls:
  - Input classification.
  - tool-call schema validation.
  - max tokens/timeouts/retry budget policy.
  - result post-filtering/redaction.

## 3) Python Library Standards Audit (Latest Docs Alignment)

Status key: `Good`, `Partial`, `Needs Change`.

| Library | Current Use | Status | Recommendation |
|---|---|---|---|
| FastAPI | Routers, DI, CORS | Partial | Keep strict allowlist CORS; add security middleware baseline and rate limit for auth endpoints. |
| Uvicorn | In-process `uvicorn.run()` | Partial | Keep for dev; use managed process deployment profile for production mode. |
| Pydantic v2 | API schemas | Partial | Set request-model `extra="forbid"` on public input models to reject unknown fields. |
| pydantic-settings | env-based settings | Good | Continue; consider typed list field for CORS instead of CSV string parsing. |
| SQLModel | SQLite models/sessions | Good | Keep session dependency pattern; add migration framework for future schema changes. |
| PyJWT | JWT create/decode | Partial | Add stronger claim validation (`exp`, `iat`, optional `aud`/`iss`) and explicit decode options. |
| passlib | password hashing | Needs Change | Move to Argon2id profile for modern password hashing baseline. |
| requests | search/http fetch | Partial | Use explicit connect/read timeouts tuple and centralized retry/backoff for external calls. |
| crewai | agent/task orchestration | Partial | Add explicit tool and output guardrails; constrain tool list by policy context. |
| litellm (indirect via CrewAI LLM config) | model/provider routing | Partial | Normalize provider+model mapping and add provider-specific validation at startup. |
| qdrant-client | vector storage | Good | Continue payload filters; add retention/TTL process for telemetry-derived vectors. |
| sentence-transformers | embeddings | Partial | Lazy-load model (avoid import-time heavy init), configurable model id, warmup checks. |
| PySide6 | desktop UI/workers | Good | Keep thread-signal approach; isolate long-running CPU/IO off UI thread (already mostly done). |
| qasync | Qt + asyncio loop | Good | Keep integration; avoid mixing blocking calls on event loop thread. |
| keyring | secret storage | Good | Keep; add UI path to clear/delete keys and failure UX for unavailable backend. |
| duckduckgo-search | fallback search | Needs Change | Migrate to maintained `ddgs` package path to avoid deprecation drift. |
| trafilatura | extraction | Partial | Add deterministic extraction limits and fallback parser path for malformed pages. |
| watchdog | folder watch | Good | Keep; add debounce and backpressure when large write bursts occur. |
| easyocr + Pillow | OCR | Partial | Initialize OCR reader once per worker pool; avoid per-request cold start. |
| pypdf | PDF extraction | Partial | Handle encrypted PDFs and extraction strictness explicitly. |
| python-docx | DOCX extraction | Good | Keep paragraph extraction; add size/page bounds for large docs. |
| lxml | transitive parser need | Good | Keep pinned with trafilatura compatibility. |
| email-validator | email schema support | Good | Keep via `EmailStr`; no changes required. |
| qt-material | desktop theming | Good | Keep optional; document fallback theme if package unavailable. |

## 4) High-Value Refactors and Code Edits

### P0 (Do First)
1. Bridge authentication for desktop ingest endpoint.
   - Add required bearer token/header check in `backend/desktop/services/api_server.py`.
   - Generate per-session random token in desktop main process and pass to bridge process.
2. Harden auth baseline for web mode.
   - Move JWT signing key to strong required secret on startup.
   - Add login attempt throttling + temporary lockout (IP/email tuple).
3. Strengthen request model boundaries.
   - Set `model_config = {"extra": "forbid"}` for public request DTOs in `backend/common/models/schemas.py`.
4. Replace frontend `localStorage` token strategy for web mode.
   - Use HttpOnly secure cookie session (or split tokens + short expiry + rotation if bearer is retained).

### P1
1. Password hashing upgrade.
   - Transition from `pbkdf2_sha256` to Argon2id in `backend/common/services/auth/auth_utils.py`.
2. Search egress controls.
   - Add domain allowlist/denylist and request budget in `backend/common/services/search/web_search.py`.
3. Privacy minimization in telemetry.
   - Store clipboard hash+URL only by default; gate raw clipboard text behind explicit "expanded capture" consent.
4. Lazy heavy-model initialization.
   - Move `SentenceTransformer` initialization out of module import in `vector_db.py`.
   - Remove unused embedder startup from `backend/desktop/services/ai_worker.py`.

### P2
1. Replace ad-hoc SQLite migration with migration tool (Alembic or SQLModel-compatible migration flow).
2. Introduce structured event schema versioning for telemetry payloads.
3. Continue the completed split from the old monolithic newsletter service into:
   - provider factory,
   - tool policy resolver,
   - crew task builder,
   - execution orchestrator.

## 5) Historical Feature-Parity Roadmap

### Phase A: Security baseline parity
- Policy engine for tool execution scope.
- Authenticated gateway profile for remote access.
- Audit trail for policy decisions and tool calls.

### Phase B: Controlled autonomy parity
- Per-task capabilities contract.
- Explicit approval checkpoints for sensitive actions.
- Replayable run artifacts (prompts, tool calls, outputs, redactions).

### Phase C: Enterprise privacy posture
- Encryption at rest for sensitive local stores.
- Data retention controls per artifact type.
- Export/delete lifecycle controls by user/session.

## 6) Practical Next Changes for This Repo

1. Add a new `security_policy.py` and enforce before each external tool call.
2. Add `BRIDGE_INGEST_TOKEN` flow between desktop main and bridge server.
3. Add `AUTH_RATE_LIMIT_*` env settings + middleware/dependency.
4. Update schemas with strict input boundaries and explicit length constraints.
5. Add a `docs/security.md` with threat model + trust boundaries + deployment modes.

## 7) External References

### Historical external references
- https://docs.openclaw.ai/docs/platform/security/
- https://docs.openclaw.ai/docs/platform/core/sandboxing/
- https://docs.openclaw.ai/docs/platform/gateway/remote/
- https://docs.openclaw.ai/docs/platform/gateway/protocol/

### Core backend
- FastAPI CORS: https://fastapi.tiangolo.com/tutorial/cors/
- FastAPI OAuth2/JWT guide: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Pydantic (models/settings): https://docs.pydantic.dev/latest/
- SQLModel FastAPI sessions: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Uvicorn settings: https://www.uvicorn.org/settings/
- PyJWT docs: https://pyjwt.readthedocs.io/en/stable/usage.html
- Passlib CryptContext: https://passlib.readthedocs.io/en/stable/lib/passlib.context.html
- Requests quickstart: https://requests.readthedocs.io/en/latest/user/quickstart/
- Qdrant client docs: https://python-client.qdrant.tech/
- Sentence Transformers docs: https://www.sbert.net/docs/sentence_transformer/usage/usage.html

### Desktop/ingestion
- Qt for Python docs: https://doc.qt.io/qtforpython-6/
- qasync README: https://github.com/CabbageDevelopment/qasync
- keyring docs: https://keyring.readthedocs.io/en/latest/
- watchdog quickstart: https://python-watchdog.readthedocs.io/en/stable/quickstart.html
- pypdf docs: https://pypdf.readthedocs.io/en/stable/
- python-docx docs: https://python-docx.readthedocs.io/en/latest/user/quickstart.html
- trafilatura core functions: https://trafilatura.readthedocs.io/en/latest/corefunctions.html
- Pillow image API: https://pillow.readthedocs.io/en/stable/reference/Image.html
- EasyOCR docs: https://www.jaided.ai/easyocr/documentation/
- duckduckgo-search package notice: https://pypi.org/project/duckduckgo-search/
