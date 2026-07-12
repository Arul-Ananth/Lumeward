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
API client and the server's runtime configuration. Do not store server secrets
in frontend environment variables or browser storage.

## Verification

```powershell
npm run lint
npm run build
```

The production build is written to `frontend/dist/`. That directory is
generated and must not be committed.

## Authentication

The frontend supports Lumeward's server authentication modes. Trusted-LAN mode
uses the server's shared trusted identity and must only be exposed on a trusted
network. Interactive mode uses the sign-up, sign-in, session-status, and logout
routes provided by the backend.
