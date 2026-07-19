# Lumeward Runtime Modes

This is the operator-facing source of truth for current runtime behavior.

## Desktop

Start the PySide application with desktop dependencies:

```powershell
cd C:\Dev\lumeward
.\venv_win\Scripts\uv.exe run --extra desktop lumeward --mode desktop
```

Desktop has two product profiles:

- **Local:** fixed local identity, SQLite, embedded Qdrant, local generation,
  optional local collectors, OCR, screen capture and file drop.
- **Enterprise client:** configure the Enterprise Server URL in Settings,
  restart, authenticate with an individual account, and select an authorized
  workspace. Generation and explicitly shared context go to that workspace.

Enterprise generation can legitimately take longer than ordinary API calls.
Its read timeout defaults to 300 seconds and can be changed with
`ENTERPRISE_GENERATION_TIMEOUT_SECONDS`; connect and ordinary request budgets
use `ENTERPRISE_CONNECT_TIMEOUT_SECONDS` and
`ENTERPRISE_REQUEST_TIMEOUT_SECONDS`.

Local/private context is not uploaded merely because a server URL exists.
File drops are explicit actions. Clipboard text is shared only when telemetry,
clipboard collection and raw-text storage are all enabled by the user.

## Server

```powershell
cd C:\Dev\lumeward
.\scripts\dev\windows\start_server.ps1
```

Useful overrides:

```powershell
.\scripts\dev\windows\start_server.ps1 -HostAddress 0.0.0.0 -Port 8000
.\scripts\dev\windows\start_server.ps1 -AuthMode interactive
.\scripts\dev\windows\start_server.ps1 -QdrantDirectory D:\Lumeward\qdrant
```

The Windows development launcher uses bundled Qdrant from the selected
directory and runs preflight checks before starting FastAPI. Direct server
launches remain supported for deployments that configure an external Qdrant.

Required server configuration:

- PostgreSQL `DATABASE_URL`.
- `QDRANT_URL` and either `QDRANT_MODE=external` or `QDRANT_MODE=bundled`.
- `SECRET_KEY` for interactive authentication.
- Appropriate bind host, CORS origins and deployment network controls.

Server startup creates missing application tables and idempotently adds the
event-ownership columns and active-organization-membership uniqueness index
needed by older databases. It does not use a schema version table. The database
itself and its role must already exist.

`scripts/dev/database.py` provides status, initialize and explicitly confirmed
destructive refresh commands for disposable development databases. These are
not normal startup requirements.

### Qdrant profiles

- `external`: an administrator starts and maintains Qdrant.
- `bundled`: Lumeward starts a configured native Qdrant executable, waits for
  readiness and stops the child process on shutdown.

Bundled Qdrant should bind to loopback and use a dedicated storage directory and
API key. See `docs/deployment/enterprise-packaging.md`.

## Authentication

### Shared

`AUTH_MODE=shared` uses one synthetic identity. The legacy value
`trusted_lan` and `TRUSTED_LAN_MODE` remain accepted for older configurations.
Use shared mode only for local demos or a trusted private network where shared
identity and shared history are acceptable.

### Interactive

`AUTH_MODE=interactive` gives each user an individual email/password identity
and opaque bearer session. It is required for enterprise workspace membership,
personal feed behavior and revocation. Web self-signup atomically creates an
immediately active organization and its first administrator; the administrator
must then create the first workspace. The older user-only signup remains for
desktop compatibility. OIDC and centralized provisioning are future options,
not requirements for the current release.

Invitation email is optional. Configure `FRONTEND_PUBLIC_URL`,
`INVITATION_EXPIRE_DAYS` and `SMTP_*` for delivery. Create/resend operations
always return a copyable single-use link even when SMTP is unavailable.

Interactive mode still requires TLS, reverse-proxy policy, strong secrets,
logging and normal enterprise deployment controls when exposed beyond localhost.

## Enterprise authorization

- Organizations contain workspaces.
- Users must belong to both an organization and a workspace.
- Requests select a workspace through `X-Workspace-ID`.
- SQL and Qdrant retrieval apply authorized user, workspace and organization scopes.
- Tags have personal preference weights and workspace policies.
- Plugin manifests and grants are stored independently, but plugins do not execute yet.

The interactive web UI separates the organization administration portal from
the user workspace. Organization administrators manage people, invitations,
workspaces, shared context, organization settings and audit activity. Workspace
administrators are limited to assigned-workspace people, shared context and tag
policies. Ordinary members use the briefing and personal features under
`/workspace`.

## Model connectivity

- Normal provider mode uses Ollama, an OpenAI-compatible provider or Gemini.
- Remote engine mode sends model-generation requests to `ENGINE_BASE_URL` while
  Lumeward keeps identity, authorization, memory and persistence on its host.
- Remote engine mode is not general remote code execution.

## Precedence

Runtime settings resolve in this order:

1. CLI flags.
2. Environment variables and `.env`.
3. Code defaults.

`--mode desktop` overrides `APP_MODE=SERVER`; `--auth-mode interactive`
overrides the configured server auth mode for that process.
