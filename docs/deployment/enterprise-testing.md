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

1. On `/signup`, enter the administrator name, email, password, organization
   name and agreement checkbox. Submission should create and activate the
   organization, sign in the administrator and open first-workspace onboarding.
2. Create the first workspace. The browser should open `/admin/overview` and
   show one member and one workspace.
3. Open **People**, choose **Invite person**, enter a new email and assign the
   workspace as `Member`. Create the invitation and copy its link. SMTP is
   optional; when delivery is unavailable the invitation and copyable link must
   remain usable.
4. Open the link in a private browser window. The invitation must display the
   organization, role and workspace. Set the new user's name and password, then
   accept it. The new member should enter `/workspace` without seeing admin
   navigation.
5. Back in the administrator session, search for the member. Change the
   workspace role to `Workspace admin`, save access, and confirm the member can
   open only **People** and **Shared context** for that workspace.
6. In **Shared context**, create a tag and share tagged text. Optionally upload a
   ZIP; this admin upload must be workspace-shared. Open `/workspace` as the
   member and verify the selected workspace can use that shared context.
7. In **People**, deactivate the member and confirm the private session can no
   longer access authenticated routes. Reactivate the member and restore the
   desired workspace assignment.
8. Open **Audit** and confirm the invitation, membership and shared-context
   actions are present without passwords or raw invitation tokens.

Private user uploads remain under `/workspace`. Administration uploads under
`/admin/context` are explicitly workspace-shared. Briefing generation also
requires a configured model provider.

## Automated checks

From the repository root:

```powershell
.\venv_win\Scripts\python.exe -m pytest tests\server
.\venv_win\Scripts\python.exe -m compileall backend
cd frontend
npm test
npm run lint
npm run build
```

## Desktop client

Keep the server running and start this in another terminal:

```powershell
cd C:\Dev\lumeward
$env:ENTERPRISE_SERVER_URL = "http://127.0.0.1:8000"
.\venv_win\Scripts\uv.exe run --extra desktop lumeward --mode desktop
```

Sign in and select an authorized workspace. Server and desktop are designed to
run concurrently.
