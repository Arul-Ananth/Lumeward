# Verification and Resume Checklist

## Last known verification

The following checks passed on the source computer after the administration
portal implementation:

- backend server suite: 26 tests passed;
- focused administration backend tests: 13 tests passed;
- frontend: 3 test files and 5 tests passed;
- frontend lint passed;
- frontend production build passed;
- Python backend compilation passed;
- `git diff --check` passed.

The Python run emitted existing `datetime.utcnow` and passlib/argon2 warnings;
they did not fail the checks. A live Vite page returned HTTP 200, but an in-app
browser instance was unavailable, so visual and click-through testing remains a
manual requirement.

## Reproduce from the repository root

Install the locked Python environment appropriate to the computer. On the
existing Windows development setup:

```powershell
.\venv_win\Scripts\uv.exe sync --extra dev
```

Run backend checks:

```powershell
.\venv_win\Scripts\python.exe -m pytest tests\server
.\venv_win\Scripts\python.exe -m pytest tests\server\test_admin_portal.py tests\server\test_admin_services.py
.\venv_win\Scripts\python.exe -m compileall backend
```

Run frontend checks:

```powershell
cd frontend
npm ci
npm test
npm run lint
npm run build
cd ..
```

Check the working tree:

```powershell
git diff --check
git status --short
```

## Manual verification still required

Use `../deployment/enterprise-testing.md` for the complete two-user flow. At a
minimum, verify:

- signup creates and signs in an organization administrator;
- first-workspace onboarding cannot be skipped;
- the responsive admin shell works at phone, tablet, desktop and 200% zoom;
- invitation acceptance works for both a new user and an existing signed-in
  user with the invited email;
- copy-link recovery works when SMTP is absent or fails;
- role and workspace assignment changes have the expected scope;
- the final active organization administrator is protected;
- deactivation revokes active sessions;
- members cannot access admin routes or cross-organization data;
- private `/workspace` uploads never appear in another user's shared context;
- audit events omit passwords, raw tokens and secrets.

## Environment data that Git does not restore

- `.env` and all credentials;
- PostgreSQL data and backups;
- Qdrant collections and local Qdrant storage;
- generated `frontend/dist/` output;
- Python virtual environments and `frontend/node_modules/`;
- uncommitted files that were never included in the transferred commit/bundle.
