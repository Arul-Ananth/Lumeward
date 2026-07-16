# Server Runtime

- `backend/server/app.py` owns FastAPI creation, router registration, middleware, and lifespan.
- `backend/main.py` only selects mode and launches the server runtime.
- Routes should depend on the auth resolver and typed schemas, not direct mode flags.
- Server mode requires PostgreSQL through `DATABASE_URL` and a Qdrant service
  through `QDRANT_URL`.
- The PostgreSQL database and role must exist before first use; application tables are created at startup.
- Startup creates missing tables and idempotently adds the event-ownership columns required by older databases.
- Startup also reconciles the PostgreSQL partial unique index that permits only
  one active organization membership per user.
- `/auth` provides authentication, atomic organization signup and invitation
  acceptance. The legacy user-only signup and older organization/workspace APIs
  remain for desktop and API compatibility.
- `/admin` provides organization bootstrap and overview, member and invitation
  management, workspace management, shared context, tag policies, settings and
  audit history. Authorization is resolved server-side for every route.
- `/news` contains the briefing, feed, memory and user-workspace APIs.
- `/health/live` reports process health; `/health/ready` checks PostgreSQL and Qdrant.
