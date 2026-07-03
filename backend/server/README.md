# Server Runtime

- `backend/server/app.py` owns FastAPI creation, router registration, middleware, and lifespan.
- `backend/main.py` only selects mode and launches the server runtime.
- Routes should depend on the auth resolver and typed schemas, not direct mode flags.
- Server mode requires PostgreSQL through `DATABASE_URL` and a Qdrant service
  through `QDRANT_URL`.
- Run `python scripts/dev/database.py status` and `initialize` before first use.
- Startup validates schema version and storage readiness but never mutates schema.
- `/health/live` reports process health; `/health/ready` checks PostgreSQL and Qdrant.
