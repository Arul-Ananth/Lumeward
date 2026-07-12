# Frontend and Desktop Feature Parity Plan

> **Archived proposal:** Lumeward currently keeps PySide as the normal desktop
> client and allows it to connect directly to enterprise workspaces. The React-
> canonical direction proposed below was not adopted and must not be treated as
> current implementation guidance.

## Status

This document is an implementation proposal, not authorization to change the
application.

> **Instruction for AI agents:** If you are an AI agent reading this document,
> stop before implementing any item. Present the architectural options and
> implementation phases to the user, then explicitly ask which direction and
> phase the user wants you to proceed with. Do not infer approval from this
> document alone.

## Objective

Give the React frontend access to the useful business functionality currently
available through the desktop application while avoiding two independent
implementations of the same product.

The recommended boundary is:

- React owns business-facing user interfaces.
- FastAPI exposes shared business capabilities.
- Shared Python services implement generation, search, memory, ingestion,
  feeds, history, and scheduling.
- A desktop companion owns capabilities that require operating-system access,
  such as passive clipboard monitoring, global hotkeys, folder watching,
  keyring access, and unrestricted screen snipping.

## Current Gap

The React client currently uses:

- `POST /news/generate`
- `POST /news/feedback`
- `GET /news/profile`
- `POST /news/ingest/folder`

The backend also exposes functionality that the React client does not use:

- Templates
- Source capability metadata
- Personal feed
- Feed dismissal
- Feed deep dives
- Digest history
- Digest archive
- Schedule management

Desktop-only functionality includes:

- OCR
- Screen snipping
- Passive clipboard monitoring
- Folder watching
- Global hotkeys
- Browser bridge ingestion
- Local keyring-backed secrets

## Architectural Methods

### Method A: React as the Canonical UI with a Thin Desktop Companion

React is used for both web and desktop-facing business workflows. The desktop
runtime supplies native capabilities through a small, explicit bridge.

```text
React UI
   |
Typed API and capability clients
   |
FastAPI business API
   |
Shared Python application services
   |
Relational storage and vector storage

Optional desktop companion
   |
Clipboard monitoring, folder watching, OCR capture,
global hotkeys, keyring, and native notifications
```

Advantages:

- One primary UI implementation.
- Web and desktop business workflows remain consistent.
- Backend business logic stays independent of presentation technology.
- Native privileges remain isolated and auditable.
- New server features become available to both surfaces.
- Capability detection can clearly communicate platform limitations.

Disadvantages:

- Requires migrating or replacing existing PySide screens.
- Requires a supported bridge between React and the desktop companion.
- Packaging becomes more complex during the transition.
- Native and browser security models still differ.
- A poorly designed bridge can become a security boundary risk.

Recommendation:

This is the preferred long-term architecture if frontend and desktop parity is
a product requirement.

### Method B: Keep Independent React and PySide Interfaces

React and PySide remain separate clients that call the same Python services or
HTTP APIs.

Advantages:

- Lowest immediate migration risk.
- Existing PySide functionality remains intact.
- Native workflows can use Qt APIs directly.
- The web application remains a conventional browser application.

Disadvantages:

- Every business feature needs two UI implementations.
- Visual behavior and validation will continue to drift.
- Fixes must frequently be duplicated.
- Test coverage and release effort grow with every feature.
- Developers must understand two state-management and component systems.

Recommendation:

Use only as a short transition strategy. Define a deadline or milestone for
choosing the canonical UI.

### Method C: Browser-Only Application

Remove the PySide application and deliver all functionality through React and
FastAPI.

Advantages:

- Simplest deployment model for server users.
- One UI and one client state-management approach.
- No Qt packaging or desktop process lifecycle.
- Easier remote access and centralized updates.

Disadvantages:

- Passive clipboard monitoring is not reliably available.
- Folder watching and global hotkeys cannot be reproduced by a normal page.
- Screen capture requires explicit permission on every operation.
- Clipboard and screen APIs require secure browser contexts and user gestures.
- Local-first privacy and offline operation become harder.

Recommendation:

Choose this only if native desktop collection is not a core product
differentiator.

### Method D: Desktop-Only Application

Remove or pause the React/server product and concentrate on PySide.

Advantages:

- Smallest scope for a personal local-first product.
- Best access to clipboard, screen capture, folders, and keyring.
- No need to maintain web authentication, CORS, or browser compatibility.
- Simpler privacy boundary.

Disadvantages:

- No remote browser access.
- Multi-user and hosted deployments are postponed.
- Desktop packaging remains platform-specific.
- Collaboration and centralized administration are harder.

Recommendation:

Choose this if the immediate goal is validating a single-user personal
intelligence product rather than a hosted service.

## Recommended Feature Architecture

The following sections assume Method A.

### Frontend Feature Structure

Organize code by product capability rather than by generic technical type.

```text
frontend/src/
  app/
    router.tsx
    navigation.ts
  features/
    generation/
      api.ts
      hooks.ts
      GeneratePage.tsx
      TemplateSelector.tsx
    feed/
      api.ts
      hooks.ts
      FeedPage.tsx
      FeedCard.tsx
      DeepDiveViewer.tsx
    history/
      api.ts
      hooks.ts
      HistoryPage.tsx
      DigestPage.tsx
    schedules/
      api.ts
      hooks.ts
      SchedulesPage.tsx
      ScheduleForm.tsx
    memory/
      api.ts
      hooks.ts
      MemoryPage.tsx
    ingestion/
      api.ts
      hooks.ts
      UploadPanel.tsx
    capture/
      clipboard.ts
      screenCapture.ts
      CapturePanel.tsx
  services/
    http.ts
  components/
    AppShell.tsx
    EmptyState.tsx
    ErrorState.tsx
```

Rules:

- Keep HTTP transport and authentication in `services/http.ts`.
- Keep feature-specific endpoint calls in each feature's `api.ts`.
- Keep server state out of `AuthContext`.
- Use focused custom hooks such as `useFeed` and `useSchedules`.
- Do not create generic hooks that hide endpoint behavior.
- Keep API response types explicit.

### Navigation

Implement these routes:

```text
/                       Generate
/feed                   Personal Feed
/feed/:id               Deep Dive
/history                Digest History
/history/:id            Digest Viewer
/schedules              Schedules
/memory                 Memory and Profile
/ingestion              Upload and Capture
/settings               Account and Capabilities
```

Authentication pages should remain outside the authenticated application shell.

### Server State

Two approaches are reasonable.

#### Option 1: TanStack Query

Use query keys such as:

```text
['templates']
['feed']
['history', { archived, page }]
['digest', digestId]
['schedules']
['profile']
['capabilities']
```

Advantages:

- Standardized caching and invalidation.
- Built-in loading, retry, mutation, and cancellation states.
- Optimistic dismiss and archive operations.
- Less repetitive request lifecycle code.

Disadvantages:

- Adds a frontend dependency and concepts to learn.
- Incorrect cache keys or invalidation can produce stale interfaces.
- May be excessive for a frontend with only a few requests.

Recommendation:

Use TanStack Query because the planned feed, history, schedule, and mutation
surface is large enough to justify it.

#### Option 2: Feature-Specific React Hooks

Implement request state with `useState`, `useEffect`, and focused custom hooks.

Advantages:

- No additional dependency.
- Behavior remains explicit.
- Suitable while the request surface is small.

Disadvantages:

- Repeats loading, error, retry, cancellation, and invalidation logic.
- Manual race-condition handling is required.
- Becomes difficult to maintain as mutations and cached lists increase.

Recommendation:

Use only for the first one or two parity features, or if adding dependencies is
currently prohibited.

## Exact Feature Work

### 1. Application Shell and Routing

Implement:

- Authenticated application shell.
- Sidebar or top-level navigation.
- Route-level loading and error boundaries.
- Consistent empty, loading, and error states.
- Responsive desktop and browser layouts.

Acceptance criteria:

- Every implemented business capability has a stable URL.
- Refreshing a nested URL restores the correct page.
- Unauthorized users are redirected to sign-in.
- Trusted-LAN mode enters the application without showing an irrelevant login
  form.

### 2. Generation and Templates

Use:

- `GET /news/templates`
- `POST /news/generate`

Implement:

- Template selector.
- Topic and guidance inputs.
- Generate and regenerate actions.
- Markdown result viewer.
- Copy, clear, save/download, and feedback actions.
- Visible search/capability state where relevant.

Advantages:

- Brings desktop generation behavior to the web.
- Uses existing backend orchestration.
- Avoids duplicating prompt construction in React.

Disadvantages:

- Long synchronous generation requests can time out.
- Browser download behavior differs from native save dialogs.

### 3. Personal Feed

Use:

- `GET /news/feed`
- `POST /news/feed/{feed_id}/dismiss`
- `POST /news/feed/{feed_id}/deep-dive`

Implement:

- Feed-card list.
- Priority and topic display.
- Dismiss mutation with optimistic removal and rollback.
- Deep-dive loading state.
- Deep-dive result viewer.
- Empty and failed-feed states.

Backend improvement:

`GET /news/feed` currently processes new events before returning the feed.
Separate mutation/work from reading where practical. A read endpoint should not
silently perform potentially expensive processing.

Advantages:

- Exposes the desktop application's primary personal-intelligence workflow.
- Reuses current feed scoring and deep-dive services.

Disadvantages:

- Deep dives can be slow.
- Synchronous processing can block requests.
- Optimistic updates require rollback behavior.

### 4. Digest History and Archive

Use:

- `GET /news/history`
- `GET /news/history/{digest_id}`
- `POST /news/history/{digest_id}/archive`

Implement:

- History list sorted by creation time.
- Archived/non-archived filter.
- Digest details page.
- Archive action.
- Link from generated and deep-dive results to persisted history.

Backend improvement:

- Add pagination before history becomes unbounded.
- Consider changing archive to a state-oriented `PATCH` endpoint in a future
  API version.

Advantages:

- Makes persisted output discoverable.
- Prevents generation results from being temporary UI state.

Disadvantages:

- Pagination and filter state add frontend complexity.
- Archive semantics need to remain consistent across clients.

### 5. Scheduling

Use:

- `GET /news/schedules`
- `POST /news/schedules`
- `PATCH /news/schedules/{schedule_id}`
- `DELETE /news/schedules/{schedule_id}`

Critical prerequisite:

The server currently exposes schedule CRUD, but the schedule worker is started
only by the desktop runtime. Do not present server scheduling as operational
until server-side execution exists.

#### Scheduler Option 1: In-Process FastAPI Task

Advantages:

- Fastest implementation.
- No additional service or deployment unit.
- Acceptable for one process and one instance.

Disadvantages:

- Multiple FastAPI workers can execute the same schedule.
- Application restarts interrupt polling.
- Long generation tasks compete with API traffic.
- Scaling the API also scales schedulers accidentally.

Recommendation:

Suitable only for a clearly documented single-process beta.

#### Scheduler Option 2: Dedicated Scheduler Process

Run a separate process that atomically claims due schedule rows.

Suggested fields:

```text
next_run_at
claimed_at
claim_owner
completed_at
last_error
```

Advantages:

- Avoids one scheduler per API worker.
- Clear operational ownership.
- Can restart independently.
- Supports database locking and retry behavior.

Disadvantages:

- Adds another process to deploy and monitor.
- Requires claim expiry and failure recovery.
- Requires concurrency tests.

Recommendation:

Preferred server implementation.

#### Scheduler Option 3: External Queue/Scheduler

Use a system such as Celery, RQ, or another external job platform.

Advantages:

- Mature retry and scheduling behavior.
- Supports distributed workers.
- Appropriate for high-volume generation.

Disadvantages:

- Adds infrastructure, dependencies, and operational complexity.
- Excessive for a small beta unless job execution is already a requirement.

Recommendation:

Do not introduce this until scale or reliability requirements justify it.

Frontend schedule work:

- List schedules.
- Create/edit form.
- Enable/disable action.
- Delete confirmation.
- Timezone selector.
- Display next run, last run, and failure state.

### 6. Memory and Feedback

Use:

- `GET /news/profile`
- `POST /news/feedback`

Implement:

- Searchable memory/profile list.
- Clear explanation of why each memory exists.
- Feedback confirmation and error states.

Future backend work:

- Delete memory.
- Correct memory.
- Export memory.
- Explain source references.

Advantages:

- Makes personalization observable.
- Gives users control over inferred data.

Disadvantages:

- Current API is mostly read-only.
- Raw vector payloads are not necessarily user-friendly.

### 7. Folder Upload

Use:

- `POST /news/ingest/folder`

Implement:

- Drag-and-drop ZIP upload.
- File-size and extension validation.
- Upload progress.
- Ingested/skipped/failed summary.
- Clear staged-file cleanup explanation.

Advantages:

- Existing backend safety and ingestion rules are reused.
- Works in normal browsers.

Disadvantages:

- The browser cannot watch the folder after upload.
- Large archives can exceed proxy or request timeouts.
- Current response is available only after processing completes.

Future improvement:

Move large ingestion to a job API with progress reporting.

### 8. Clipboard

#### Web Method: Explicit Clipboard Read

Implement a user-triggered “Paste from clipboard” action with the browser
Clipboard API.

Advantages:

- No desktop companion required.
- User intent and permission are explicit.
- Suitable for attaching current clipboard content to generation.

Disadvantages:

- Requires HTTPS or another secure context.
- Browser permission behavior varies.
- User interaction is normally required.
- Cannot reliably monitor clipboard changes in the background.

#### Desktop Method: Passive Collector

Keep passive clipboard collection in the desktop companion.

Advantages:

- Matches current desktop behavior.
- Supports background history and matching.

Disadvantages:

- Native-only feature.
- Requires strong consent, retention, and raw-text controls.
- Cannot provide identical behavior to remote web users.

Recommendation:

Offer explicit clipboard paste everywhere and passive collection only when the
desktop capability is present.

### 9. Screen Capture and OCR

#### Web Method: Browser Screen Capture

Implement:

1. User clicks Capture.
2. Call `navigator.mediaDevices.getDisplayMedia()`.
3. User chooses a screen, window, or tab.
4. Capture one frame into a canvas.
5. Convert the canvas to an image blob.
6. Upload the image to a new OCR endpoint.
7. Attach returned text to generation context.
8. Stop all capture tracks immediately.

Advantages:

- Works without a native companion on supported browsers.
- Permission is visible and user initiated.
- Can reuse backend OCR.

Disadvantages:

- Requires HTTPS.
- Permission cannot be silently persisted.
- Browser support varies.
- It does not reproduce arbitrary native region selection exactly.
- Users may accidentally share sensitive content.

#### Desktop Method: Native Screen Snipper

Retain the existing desktop overlay and OCR worker.

Advantages:

- Precise native region selection.
- Consistent desktop behavior.
- No browser compatibility concerns.

Disadvantages:

- Requires the desktop companion.
- Needs a React/desktop bridge if React becomes the canonical UI.

Recommendation:

Implement both behind one `CapturePanel`, selected through capability
negotiation.

### 10. Folder Watching and Global Hotkeys

These features require the desktop companion.

Implement:

- Companion status indicator.
- List of consented watched folders.
- Enable/disable controls.
- Global-hotkey configuration.
- Clear unavailable state in ordinary browser deployments.

Advantages:

- Preserves valuable native automation.
- Prevents pretending browser APIs can provide native parity.

Disadvantages:

- Requires companion installation and lifecycle management.
- Remote browser sessions cannot use local server filesystem watchers safely.

## Capability Negotiation

Add:

```http
GET /capabilities
```

Example:

```json
{
  "runtime": "server",
  "features": {
    "templates": true,
    "feed": true,
    "history": true,
    "schedules": false,
    "ocr": true,
    "screen_capture": true,
    "clipboard_read": true,
    "clipboard_monitoring": false,
    "folder_watch": false,
    "global_hotkey": false
  }
}
```

Rules:

- Report operational capabilities, not planned functionality.
- `schedules` must be false until a server scheduler is actually running.
- React should hide or disable unsupported actions with an explanation.
- Avoid scattering `APP_MODE` checks throughout React components.
- Version the capability response if its shape becomes externally consumed.

Advantages:

- One frontend can adapt to web and desktop environments.
- Native limitations become explicit.
- Reduces mode-specific conditionals.

Disadvantages:

- Incorrect capability reporting can expose broken UI paths.
- Requires integration tests for each supported capability profile.

## Long-Running Operations

Generation, deep dive, OCR, and folder ingestion may exceed ordinary HTTP
request durations.

### Method 1: Synchronous Requests

Advantages:

- Simple client and server implementation.
- Easy error propagation.

Disadvantages:

- Vulnerable to reverse-proxy and browser timeouts.
- No durable progress or retry state.
- A disconnected client loses the result presentation flow.

Recommendation:

Keep for ordinary generation during the beta if observed latency is acceptable.

### Method 2: Job API

Example:

```http
POST /news/feed/{id}/deep-dive
202 Accepted
{ "job_id": "..." }

GET /jobs/{job_id}
{ "status": "running", "progress": 40 }

GET /jobs/{job_id}/result
```

Advantages:

- Supports progress, cancellation, retries, and reconnection.
- Better for ingestion and deep dives.
- Separates HTTP request lifetime from work lifetime.

Disadvantages:

- Requires job persistence and cleanup.
- Requires authorization checks on every job.
- Polling or server-push support is needed.

Recommendation:

Implement first for folder ingestion and deep dives after real timeout or
progress requirements are observed. Do not build a generic distributed job
platform solely for architectural completeness.

## Backend Router Organization

As parity work expands, split the current news router by capability:

```text
backend/server/routers/
  generation.py
  feed.py
  history.py
  schedules.py
  ingestion.py
  memory.py
  capabilities.py
```

Each module should own an `APIRouter`. The application should include those
routers under a stable API prefix.

Advantages:

- Easier ownership and targeted testing.
- Smaller import surfaces.
- Clearer capability boundaries.

Disadvantages:

- More files and repeated router setup.
- Splitting too early can obscure a still-small API.

Recommendation:

Split when implementing frontend parity, because the existing router already
contains several independent capabilities.

## Testing Requirements

Backend:

- Contract tests for every endpoint used by React.
- Authorization tests proving users cannot access another user's data.
- Schedule claim/concurrency tests.
- Capability-profile tests.
- Pagination and archive tests.
- Long-running operation failure tests.

Frontend:

- Feature API tests.
- Loading, empty, success, and failure states.
- Optimistic update rollback tests.
- Route access tests.
- Capability-disabled UI tests.
- Clipboard and screen-capture permission-denial tests.

End to end:

- Generate with a selected template.
- Open and dismiss a feed card.
- Complete a deep dive.
- Open and archive history.
- Create, update, disable, and delete a schedule.
- Upload a ZIP and inspect the result.
- Capture or paste context where supported.

## Phased Implementation

### Phase 1: Shared Web Business Features

Implement:

- Application shell and navigation.
- Feature-specific API modules.
- Server-state strategy.
- Template selection.
- Feed, dismiss, and deep dive.
- History and archive.

Exit criteria:

- React exposes all already-operational read and mutation endpoints except
  schedules.
- Deep links and authentication work.
- Loading and error behavior are tested.

### Phase 2: Operational Scheduling

Implement:

- Dedicated server scheduler or explicitly single-process beta scheduler.
- Atomic schedule claims.
- Next-run and failure state.
- Schedule management UI.

Exit criteria:

- Schedules execute exactly once under the supported deployment topology.
- Failed jobs can be observed and retried safely.

### Phase 3: Capability-Aware Native Features

Implement:

- `/capabilities`.
- Explicit browser clipboard paste.
- Browser screen capture.
- OCR upload endpoint.
- Desktop companion capability bridge.

Exit criteria:

- Web users receive honest unavailable states.
- Desktop users can access native functionality through the canonical UI.
- Permission denial and companion disconnection are handled.

### Phase 4: Reliability and Scale

Implement only when usage justifies it:

- Job API for long-running work.
- History pagination.
- Ingestion progress.
- Scheduler retries and monitoring.
- Server-push updates if polling becomes inadequate.

## Decisions Required Before Implementation

The user must choose:

1. Which architectural method is the target:
   - React plus thin desktop companion
   - Independent React and PySide clients
   - Browser only
   - Desktop only
2. Whether React may add TanStack Query.
3. Whether server scheduling must support multiple FastAPI workers.
4. Whether screen capture and OCR are required in the first parity release.
5. Whether passive clipboard monitoring and folder watching are essential.
6. Whether placeholder source metadata should remain visible.
7. Whether the first implementation phase should include router splitting.

No implementation should begin until these decisions are confirmed by the
user.
