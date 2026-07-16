# Lumeward Web Frontend

This directory contains Lumeward's React and TypeScript web interface. Vite
serves the development UI and produces the static production bundle. The UI
connects to the Lumeward FastAPI server; it does not replace the PySide desktop
application.

## Requirements

- A supported Node.js release with `npm`
- A running Lumeward server for API-backed features

The development server listens on `http://localhost:5173`. The backend must
allow that origin through `CORS_ALLOWED_ORIGINS`.

## Install and Run

Use the tracked lock file for reproducible installs:

```powershell
cd frontend
npm ci
npm run dev
```

The backend URL and authentication behavior are defined by the shared frontend
API client and the server's runtime configuration. Provider, database and server
secrets must never be placed in frontend configuration. Interactive auth currently
stores its opaque session token in browser `sessionStorage`.

## Verification

```powershell
npm test
npm run lint
npm run build
```

The production build is written to `frontend/dist/`. That directory is
generated and must not be committed.

## Authentication

The frontend supports Lumeward's server authentication modes. Trusted-LAN mode
uses the server's shared trusted identity and must only be exposed on a trusted
network. Interactive mode uses the sign-up, sign-in, session-status, and logout
routes provided by the backend. Workspace-aware requests must send the selected
`X-Workspace-ID` header centrally.

Interactive web signup creates an organization administrator and organization in
one transaction, establishes a session, and directs the administrator to create
the first workspace. The administration routes cover overview, people and
invitations, workspaces, shared context and tag policies, organization settings,
and audit history. The existing briefing and personal-memory experience remains
available at `/workspace`.

Organization administrators see every administration route. Workspace
administrators see only People and Shared Context for their assigned workspaces,
including workspace tag policies. Ordinary members are directed to `/workspace`.
The web UI intentionally does not display social login, password reset or
remember-me controls because those capabilities are not implemented.

Invitations always return a copyable single-use link when created or resent.
Configure the `SMTP_*` and `FRONTEND_PUBLIC_URL` settings documented in
`.env.example` to deliver those links by email. Invitation tokens are stored only
as hashes and cannot be recovered later from the invitation list.
