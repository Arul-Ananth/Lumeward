# Lumeward Roadmap and Status

This document separates what is already implemented from items that are only possible future work.
Future items listed here may or may not be implemented.

## Implemented So Far

### Project and runtime

- Project rebrand to `Lumeward` and root folder rename to `C:\Dev\lumeward`
- Conservative cleanup of stale generated archive-only content from older repo history
- Operator-facing runtime/trust documentation in `modes.md`

### Startup and deployment

- CLI runtime overrides in `backend/main.py`
- centralized mode resolution and runtime override handling
- PostgreSQL connection pooling and explicit pre-release schema management for server mode
- external or localhost Qdrant service requirement for server mode
- optional remote OpenAI-compatible engine support
- outbound allowlisting for the configured remote engine target

### Auth and server posture

- explicit `trusted_lan` and `interactive` auth profiles
- interactive web auth/session path retained for authenticated deployments
- trusted-lan path preserved for private-network use

### Search and generation

- Serper search path
- desktop fallback search using `ddgs`
- explicit search-mode reporting in desktop UI/logging
- runtime-date grounding for `today/current/latest` style prompts
- direct current-date response path for date-only queries
- direct recent-clipboard context path for clipboard-history queries

### Desktop telemetry and ingestion

- desktop telemetry opt-in path
- clipboard opt-in and raw-text sensitivity split
- runtime synchronization between saved desktop preferences and clipboard collector behavior
- OCR, screen snipping, bridge ingestion, and file-drop context attachment
- server `.zip` folder upload endpoint for explicit local document indexing
- restart-based managed upload cleanup controlled through `.env`
- upload-staged files are separate from persisted relational/Qdrant state

### Personal intelligence feed

- local `intelligence_feed` persistence for lightweight feed cards
- rule-based feed scoring and dedupe before heavy generation
- Personal Feed panel in desktop mode
- server `/news/feed` endpoints for current-user feed listing, dismiss, and Deep Dive handoff
- Deep Dive reuses the existing newsletter pipeline instead of duplicating CrewAI generation

### Desktop UI

- desktop app reframed as a personal intelligence feed and deep-dive workstation
- main view restructured around Personal Feed, collapsible Guidance, and Deep Dive Viewer
- grouped settings dialog sections
- theme preference in settings:
  - `System Default`
  - `Dark`
  - `Light`
- desktop theme applies immediately without restart
- page-level scrolling through a `QScrollArea`
- result actions:
  - copy
  - regenerate
  - clear
  - save as markdown
- visible run/result debug metadata removed from the main workspace

### Desktop bridge stability

- loopback-only bridge with runtime bridge token
- bridge startup status reporting in the desktop app
- Uvicorn bridge configured with `lifespan="off"` to avoid noisy shutdown `CancelledError` traces

## Possible Future Items

These items are intentionally non-committal. They are candidates, not promises.

### UI and UX

- stronger visual polish for light mode and more distinctive desktop styling
- richer Markdown rendering and typography in the result pane
- desktop accessibility pass for contrast, spacing, and keyboard navigation
- more structured attachment chips/cards instead of plain attached-context text blocks
- optional split-view or dockable panels for activity, result, and attachments

### Desktop behavior

- better bridge health diagnostics and recovery UX
- runtime migration of old keyring/settings/data from legacy app identity names
- refined output telemetry for action buttons like explicit `Copy` button usage
- removal of deprecated `datetime.utcnow()` usage in telemetry code

### Search and grounding

- cleaner summarization of fallback search results before they reach the agent
- stronger validation on time-sensitive outputs to reject stale conflicting dates
- per-query search/tool policy profiles instead of the current shared path

### Security and deployment

- reverse proxy + TLS deployment guide for broader server exposure
- alternative auth transports such as cookies or external identity providers
- stronger session rotation/revocation controls
- per-user memory isolation improvements beyond the current trusted-lan shared identity model

### Engine and architecture

- a dedicated remote execution/job engine separated from the LLM provider path
- more explicit engine health/status visibility in the operator UI
- deeper typing of profile and response payloads
- continued removal of transitional wrapper modules after import migration finishes

## How To Read This File

- `Implemented So Far` should match current code and active behavior.
- `Possible Future Items` is a planning pool only.
- If an item becomes committed work, move it out of the future section and document the implementation in the relevant active docs.

