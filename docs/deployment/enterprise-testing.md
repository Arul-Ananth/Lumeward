# Enterprise end-to-end test

PostgreSQL must be running and the database configured in `.env` must exist.

```powershell
cd C:\Dev\lumeward
.\venv_win\Scripts\uv.exe sync --extra desktop --extra dev
.\venv_win\Scripts\uv.exe run python scripts\dev\database.py status

$env:AUTH_MODE = "interactive"
$env:QDRANT_MODE = "bundled"
$env:BUNDLED_QDRANT_BINARY = (Resolve-Path ".\tools\qdrant\qdrant.exe").Path
$env:BUNDLED_QDRANT_CONFIG_PATH = (Resolve-Path ".\packaging\qdrant\production.yaml").Path
$env:BUNDLED_QDRANT_STORAGE_DIR = "$PWD\data\qdrant-server"
.\venv_win\Scripts\uv.exe run lumeward --mode server --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd C:\Dev\lumeward\frontend
npm.cmd ci
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm.cmd run dev
```

Confirm `http://127.0.0.1:8000/health/ready`, then open
`http://127.0.0.1:5173`.

## Two-user verification

1. Sign up an administrator, sign in, and create an organization and workspace.
2. In a private browser window, sign up a second user, then return to the admin session.
3. Enter the second user's email under **Add member**. Basic organization and
   workspace membership are granted without administrative access.
4. Create a tag, select it, share team context with a descriptive title, and
   click **Refresh team feed**. The item should appear for the administrator.
5. Sign in as the member and select the same workspace. Set that tag to **Mute**
   before refreshing; the tagged item should not enter that user's feed.
6. Set the tag to **Prefer**, have the administrator share a new tagged item,
   then refresh the member feed. The new item should receive a personal boost.
7. Generate a briefing from both accounts to verify selected-workspace context.

ZIP folder uploads remain private to the uploader. Use **Team context** for
explicit workspace sharing. Generation also requires the configured model provider.

## Desktop client

Keep the server running and start this in another terminal:

```powershell
cd C:\Dev\lumeward
$env:ENTERPRISE_SERVER_URL = "http://127.0.0.1:8000"
.\venv_win\Scripts\uv.exe run --extra desktop lumeward --mode desktop
```

Sign in and select an authorized workspace. Server and desktop are designed to
run concurrently.
