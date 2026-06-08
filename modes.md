# Lumeward Modes

`modes.md` is the operator-facing source of truth for how Lumeward runs today.

## Runtime Modes

### `DESKTOP`

Intended use:
- local single-user desktop workflow
- clipboard, OCR, screen snipping, drag-drop, and browser-bridge ingestion

How it starts:

```powershell
cd C:\Dev\lumeward
.\venv_win\Scripts\python.exe backend\main.py --mode desktop
```

Auth/sign-in:
- no browser sign-in
- desktop mode resolves to the local desktop identity path

Exposure:
- local machine only
- bridge server stays on loopback

Required config:
- `.env` with an LLM provider or remote engine settings
- optional API keys in desktop settings/keyring

Trust boundary:
- safe for local operator workflows
- not intended to be exposed directly over the network

### `SERVER`

Intended use:
- backend API for browser clients
- LAN or broader server deployment depending on auth profile and hardening
- explicit `.zip` folder upload for local indexing through the React frontend or `/news/ingest/folder`

How it starts:

```powershell
cd C:\Dev\lumeward
.\venv_win\Scripts\python.exe backend\main.py --mode server
```

Useful overrides:

```powershell
.\venv_win\Scripts\python.exe backend\main.py --mode server --host 0.0.0.0 --port 8000
.\venv_win\Scripts\python.exe backend\main.py --mode server --auth-mode interactive
```

Auth/sign-in:
- depends on the auth profile described below

Exposure:
- can be LAN-only or more broadly exposed depending on deployment hardening

Required config:
- `.env`
- `SECRET_KEY` for interactive server deployments
- `CORS_ALLOWED_ORIGINS`
- optional folder upload controls:
  - `FOLDER_UPLOAD_ENABLED`
  - `FOLDER_UPLOAD_DIR`
  - `FOLDER_UPLOAD_DELETE_ON_RESTART`
  - `FOLDER_UPLOAD_MAX_ARCHIVE_MB`
  - `FOLDER_UPLOAD_MAX_FILES`

Trust boundary:
- do not treat raw server mode as internet-safe by default
- deployment posture depends on auth mode, reverse proxy, TLS, and network controls
- uploaded source files are staged under `DATA_DIR / FOLDER_UPLOAD_DIR`; cleanup applies only to that managed staging area

## Auth / Trust Profiles

### `trusted_lan`

Intended use:
- private LAN environments where one shared synthetic identity is acceptable

How it is selected:
- `AUTH_MODE=trusted_lan`
- or legacy fallback `TRUSTED_LAN_MODE=true`
- desktop mode also resolves to trusted-lan behavior internally

Sign-in required:
- no

Exposure:
- private network only

Required config:
- `AUTH_MODE=trusted_lan`
- optional `TRUSTED_LAN_USER_EMAIL`
- optional `TRUSTED_LAN_USER_NAME`

Security limitations:
- memory/profile state is shared for the trusted identity
- unsuitable for hostile or public networks

### `interactive`

Intended use:
- authenticated server deployments where each user signs in

How it is selected:
- `AUTH_MODE=interactive`
- or `--auth-mode interactive` in server mode

Sign-in required:
- yes

Exposure:
- safer basis for broader deployment than `trusted_lan`, but still needs normal hardening

Required config:
- `SECRET_KEY`
- `AUTH_MODE=interactive`
- server host/port/CORS settings

Security limitations:
- still requires TLS, reverse proxy, cookie/session policy review, and normal public deployment controls

### `untrusted`

This is an operator-facing deployment label, not a separate enum in the code.

Meaning:
- `untrusted` refers to running Lumeward in `SERVER` mode with the `interactive` auth profile and appropriate deployment hardening

Use it when:
- the network is not fully trusted
- the service may be reachable outside a private LAN

Practical mapping:
- runtime mode: `SERVER`
- auth mode: `interactive`

## Connectivity Profiles

### Local provider mode

Meaning:
- Lumeward talks directly to the configured LLM provider from the backend/runtime

Examples:
- Ollama on the same machine
- direct OpenAI-compatible endpoint
- direct Gemini provider path

Relevant config:
- `LLM_PROVIDER`
- `OPENAI_API_BASE`
- `OPENAI_MODEL_NAME`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

When to use:
- local development
- direct provider integrations

### Remote engine mode

Meaning:
- Lumeward sends model requests to an OpenAI-compatible engine running on another machine

Relevant config:
- `ENGINE_ENABLED=true`
- `ENGINE_BASE_URL`
- `ENGINE_API_KEY`
- `ENGINE_MODEL_NAME`
- `ENGINE_TIMEOUT_SECONDS`
- `ENGINE_MAX_RETRIES`

When to use:
- central model gateway deployments
- dedicated model-serving machine or service

Security expectations:
- backend-to-engine traffic only
- API-key authenticated
- engine stays private to Lumeward
- outbound policy only allows the configured engine origin

## Deployment Interpretations

### Desktop local mode

Mapping:
- runtime: `DESKTOP`
- auth behavior: trusted-lan style local identity
- connectivity: local provider or remote engine

Best for:
- personal workstation use
- privacy-first local workflows

### Server trusted LAN mode

Mapping:
- runtime: `SERVER`
- auth: `trusted_lan`

Best for:
- home lab
- office LAN prototype use

Do not use for:
- public or semi-trusted internet exposure

### Server untrusted / interactive mode

Mapping:
- runtime: `SERVER`
- auth: `interactive`
- operator-facing label: `untrusted`

Best for:
- authenticated multi-user server deployment

Required hardening:
- strong `SECRET_KEY`
- TLS/reverse proxy
- CORS review
- session/auth review
- standard public-service logging and monitoring

## Precedence Rules

Lumeward resolves startup settings in this order:

1. CLI flags
2. environment variables
3. code defaults

Examples:
- `--mode desktop` overrides `APP_MODE=SERVER`
- `--auth-mode interactive` overrides `AUTH_MODE=trusted_lan`
- `--host` and `--port` override server env values in server mode only

## Practical Commands

Desktop:

```powershell
.\venv_win\Scripts\python.exe backend\main.py --mode desktop
```

Trusted-LAN server:

```powershell
.\venv_win\Scripts\python.exe backend\main.py --mode server --auth-mode trusted_lan --host 0.0.0.0 --port 8000
```

Interactive server:

```powershell
.\venv_win\Scripts\python.exe backend\main.py --mode server --auth-mode interactive --host 0.0.0.0 --port 8000
```

Remote engine:

```env
ENGINE_ENABLED=true
ENGINE_BASE_URL=http://192.168.1.50:8001/v1
ENGINE_API_KEY=replace_me
ENGINE_MODEL_NAME=my-remote-model
ENGINE_TIMEOUT_SECONDS=30
ENGINE_MAX_RETRIES=2
```

Server folder upload:

```env
FOLDER_UPLOAD_ENABLED=true
FOLDER_UPLOAD_DIR=uploads/folders
FOLDER_UPLOAD_DELETE_ON_RESTART=true
FOLDER_UPLOAD_MAX_ARCHIVE_MB=10240
FOLDER_UPLOAD_MAX_FILES=500
```

Upload endpoint:

```text
POST /news/ingest/folder
```

The React Dashboard exposes this as `Upload Folder` in server mode. Uploads must be `.zip` archives. Staged upload files are kept until the next server restart when cleanup is enabled.

## Current Constraints

- `untrusted` is documented terminology only; the code still uses `interactive`
- desktop mode always resolves to trusted-lan style auth behavior
- remote engine mode is for model requests, not general remote code execution
- server folder upload is explicit archive ingestion, not live server-side folder watching
- current public-internet posture still requires additional deployment hardening beyond the repo defaults
