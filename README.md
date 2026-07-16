# Lumeward

Current release target: `1.0.0-beta.1`.

Lumeward is a hybrid AI brief/newsletter application with shared backend services and two runtime modes:

- `SERVER` for web clients
- `DESKTOP` for the PySide6 desktop app

## Current Implemented State

### Core runtime

- CLI startup overrides are implemented in `backend/main.py`:
  - `--mode {desktop,server}`
  - `--auth-mode {shared,trusted_lan,interactive}`
  - `--host`
  - `--port`
  - `--reload`
- Runtime precedence is:
  - CLI flags
  - environment variables
  - code defaults

### Auth and deployment

- Web/server mode supports:
  - `AUTH_MODE=shared` (`trusted_lan` remains a legacy alias)
  - `AUTH_MODE=interactive`
- Desktop mode supports a local identity or an interactive connection to an enterprise server.
- `modes.md` is the operator-facing source of truth for runtime and trust modes.

### Remote engine support

- Lumeward can call an OpenAI-compatible engine running on another machine.
- When enabled, Lumeward keeps auth, memory, telemetry, persistence, and tool policy locally and sends only model requests to the remote engine.
- Server deployments can use this for users who cannot host an LLM locally but can reach a dedicated trusted model machine.
- Configure it with:
  - `APP_MODE=SERVER`
  - `ENGINE_ENABLED=true`
  - `ENGINE_BASE_URL=https://trusted-engine.example/v1`
  - `ENGINE_API_KEY=...`
  - `ENGINE_MODEL_NAME=...`

### Newsletter curation

- Active newsletter orchestration lives in `backend/common/services/newsletter/`.
- The pipeline retrieves local memory, sanitizes context, runs allowed web search, calls the configured LLM provider or remote engine, compiles Markdown and safe HTML, and persists digest history.
- Built-in templates include Daily Tech Briefing, Weekly Research Digest, Morning Digest, and Current Events Summary.
- Server `/news` APIs support generation, digest history/archive, templates, and schedules.

### Server folder upload

Server mode supports explicit folder ingestion through `.zip` uploads. Uploaded archives and extracted files are staged under the managed data directory and are deleted only on the next server startup when cleanup is enabled.

Configure cleanup and limits in `.env`:

```env
FOLDER_UPLOAD_ENABLED=true
FOLDER_UPLOAD_DIR=uploads/folders
FOLDER_UPLOAD_DELETE_ON_RESTART=true
FOLDER_UPLOAD_MAX_ARCHIVE_MB=250
FOLDER_UPLOAD_MAX_EXPANDED_MB=1000
FOLDER_UPLOAD_MAX_FILES=500
```

Upload a zipped folder:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/news/ingest/folder `
  -Form @{ file = Get-Item .\my-folder.zip }
```

Only `.txt`, `.md`, `.html`, `.pdf`, and `.docx` files are indexed. Indexed
memory remains in the active relational database and Qdrant after staged upload
files are cleaned up.

### Desktop telemetry and clipboard

- Desktop telemetry is opt-in.
- Telemetry is disabled by default until the user enables data collection in desktop settings or env.
- Clipboard collection is opt-in.
- Raw clipboard text is separately opt-in.
- Recent clipboard-history queries use a direct recent-clipboard path instead of only semantic memory retrieval.

### Search behavior

- Serper is used when a Serper key is available.
- Desktop fallback search uses `ddgs` + extraction when Serper is unavailable.
- Server fallback search is disabled unless `ALLOW_SERVER_DDG_FALLBACK=true` is explicitly set.
- Search mode is surfaced in the desktop UI.

### Desktop UI

- The desktop UI is now framed as a personal intelligence feed and deep-dive workstation.
- The main desktop screen is organized around:
  - `Personal Feed`
  - collapsible `Guidance`
  - `Deep Dive Viewer`
- Desktop settings include theme preference:
  - `System Default`
  - `Dark`
  - `Light`
- Theme changes apply immediately without restart.
- The main desktop view is wrapped in a scroll area so the whole screen can be reached with the mouse wheel.
- Enterprise users can configure a server URL, authenticate, select a workspace,
  generate against authorized workspace context, and explicitly share supported files or opted-in collector context.

### Enterprise foundations

- Interactive users have individual identities and opaque server sessions.
- Organizations, workspaces, memberships, scoped context, tags, user tag preferences,
  workspace tag policies, plugin manifests, and independent plugin grants are implemented.
- The web UI provides a dedicated organization-administration portal with
  self-service organization signup, required first-workspace onboarding,
  role-aware people and workspace management, email invitations with copy-link
  fallback, shared-context and tag-policy controls, and organization audit
  history. Briefings and personal memory remain in a separate workspace view.
- Plugin execution and plugin-driven ingestion remain future work.
- The current web release uses individual email/password sessions. OIDC and
  external enterprise provisioning remain future authentication options.

### Desktop bridge

- The local browser bridge stays on loopback.
- It uses a runtime-generated bridge token header.
- Uvicorn lifespan handling is disabled for the bridge app to avoid noisy shutdown `CancelledError` traces.

## Project Layout

- `backend/` shared backend, server mode, desktop mode
- `frontend/` React + Vite web client
- `docs/` architecture, audits, prompts, roadmap/status notes
- `scripts/verify/` verification scripts
- `scripts/manual/` manual checks
- `scripts/dev/` build and operational scripts
- `packaging/pyinstaller/` desktop packaging specs

## Dependency Locking

`pyproject.toml` supports a standard uv-managed development environment:

```powershell
.\venv_win\Scripts\uv.exe sync
.\venv_win\Scripts\uv.exe sync --extra desktop
.\venv_win\Scripts\uv.exe sync --extra dev
.\venv_win\Scripts\uv.exe sync --extra packaging
```

`uv sync` creates and manages `.venv`. The existing `venv_win` remains usable
with the lock-file workflow below.

Python dependencies use human-edited `.in` files and generated `.lock.txt`
files. Use the lock files for reproducible installs:

```powershell
.\venv_win\Scripts\python.exe -m pip install uv
.\venv_win\Scripts\python.exe -m uv pip sync --torch-backend cpu requirements-server.lock.txt
```

Edit the matching `.in` file when changing direct dependencies, then regenerate
the lock:

```powershell
.\venv_win\Scripts\python.exe -m uv pip compile --universal --no-strip-markers --torch-backend cpu requirements-server.in -o requirements-server.lock.txt
```

The `.in` files are the human-edited dependency inputs. Production, server,
desktop, and packaging installs must use the matching generated lock file.

## Testing

Backend tests use pytest and default to local deterministic checks:

```powershell
.\venv_win\Scripts\python.exe -m pytest tests
```

Use `scripts/verify/` for targeted smoke checks that have not yet been converted
to pytest or that need live integrations.

## Beta Packaging

Lumeward Beta 1.0 desktop packaging uses the tracked PyInstaller spec as the build source of truth:

```powershell
.\scripts\dev\windows\build_windows.ps1
```

macOS and Linux build entrypoints are available at:

```bash
./scripts/dev/macos/build_macos.sh
./scripts/dev/linux/build_linux.sh
```

Packaging outputs are:
- folder app: `dist/Lumeward/`
- Windows installer: generated when Inno Setup `iscc` is available
- macOS DMG: generated when `hdiutil` is available
- Linux AppImage: generated when `appimagetool` is available

Run preflight before packaging:

```powershell
.\venv_win\Scripts\python.exe scripts\dev\preflight.py
```

Install packaging dependencies before building executables:

```powershell
.\venv_win\Scripts\python.exe -m pip install uv
.\venv_win\Scripts\python.exe -m uv pip sync --torch-backend cpu requirements-packaging.lock.txt
```

Beta 1.0 stores plugin manifests and independently scoped permission grants as a future-facing foundation. It does not execute plugins or ingest plugin context yet.

## Startup

Server:

```powershell
cd C:\Dev\lumeward
.\venv_win\Scripts\uv.exe run lumeward --mode server
```

Server mode requires PostgreSQL. Qdrant may be administrator-managed
(`QDRANT_MODE=external`) or a native executable owned by the Lumeward server
(`QDRANT_MODE=bundled`). Server startup creates missing application tables and
idempotently reconciles the event-ownership columns plus the
one-active-organization-membership index; it does not use schema versions.

The development database helper still supports explicitly confirmed destructive refreshes:

```powershell
.\venv_win\Scripts\python.exe scripts\dev\database.py refresh --confirm lumeward
.\venv_win\Scripts\python.exe scripts\dev\database.py refresh-all --confirm lumeward
```

`refresh` deletes PostgreSQL application data. `refresh-all` also deletes and
recreates Lumeward's Qdrant collections. Neither command runs during startup.

Desktop:

```powershell
cd C:\Dev\lumeward
.\venv_win\Scripts\python.exe backend\main.py
```

Interactive server:

```powershell
.\venv_win\Scripts\python.exe backend\main.py --mode server --auth-mode interactive --host 0.0.0.0 --port 8000
```

## Docs

- [modes.md](./modes.md): runtime modes, trust profiles, connectivity profiles
- [docs/architecture/overview.md](./docs/architecture/overview.md): current codebase structure and implementation shape
- [docs/security.md](./docs/security.md): trust boundaries and safeguards
- [docs/deployment/enterprise-testing.md](./docs/deployment/enterprise-testing.md): exact two-user end-to-end test
- [docs/roadmap.md](./docs/roadmap.md): implemented work so far plus possible future items that may or may not happen
- [docs/context-restoration/README.md](./docs/context-restoration/README.md): temporary cross-computer handoff for the current portal work

## Future Items

Potential future work is tracked in [docs/roadmap.md](./docs/roadmap.md).
Those items are directional only unless explicitly scheduled; they are not commitments.



## Linux Desktop Setup

For Linux or WSL desktop testing, use the Linux-specific desktop lock file:

```bash
cd /mnt/c/Dev/lumeward
python3 -m venv .venv_linux
source .venv_linux/bin/activate
python -m pip install --upgrade pip setuptools wheel uv
python -m uv pip sync --torch-backend cpu requirements-desktop-linux.lock.txt
python backend/main.py --mode desktop
```

Recommended OS packages on Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y python3-venv libgl1 libglib2.0-0 libxkbcommon-x11-0 libdbus-1-3 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 gnome-keyring libsecret-1-0 libsecret-1-dev dbus-user-session
```

Notes:
- `requirements.in` includes the CrewAI Google provider extra used by `LLM_PROVIDER=google`.
- `requirements-desktop-linux.lock.txt` installs Linux keyring backends so desktop secret access works more reliably for other developers.
- In WSL, a working GUI environment is still required for PySide6 desktop mode.

## macOS Desktop Notes

Desktop data defaults to `~/Library/Application Support/Lumeward`.
macOS may prompt for user approval when a source plugin or collector accesses protected locations such as Desktop, Documents, Downloads, screen capture, or automation. Prefer user-selected folders and official service APIs over direct reads of other apps' private storage.
