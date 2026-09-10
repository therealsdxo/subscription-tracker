# Goals

1. You're a senior backend engineer with 15–20 years of experience building
   production FastAPI services. Work strictly from `project.md`, the answered
   `progress/questionnaire.md`, and `progress/tech_doc.md`. Do not invent
   requirements — if something is genuinely undecided, list it as an open
   question instead of guessing.

2. Scaffold the backend service only. This phase produces a runnable skeleton
   and the project's foundations — **no business features yet** (customers,
   packages, subscriptions, deliveries, payments come in later phases per the
   milestones in `tech_doc.md` §16).

3. Restructure the repository to match `tech_doc.md` §15:
   - Create `backend/` with the `app/` package (`core/`, `models/`, `schemas/`,
     `api/v1/routers/`, `services/`, `repositories/`, `workers/`).
   - Remove the throwaway prototype: root `tools.py` and
     `src/subscription_tracker/`.
   - Keep `progress/` untouched.

4. Set up tooling and dependencies with `uv` (Python 3.13):
   - FastAPI, Uvicorn, Pydantic v2, `pydantic-settings`
   - SQLAlchemy 2.x, Alembic, `psycopg` (v3) driver
   - `argon2-cffi` (password hashing), `pyjwt` (or `python-jose`) for JWT
   - Dev group: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`
   - Pin versions in `pyproject.toml`; commit the refreshed `uv.lock`.

5. Application foundations (no domain logic):
   - `app/main.py` — FastAPI app factory, versioned router mount at `/api/v1`,
     CORS for the frontend origin, exception handlers that emit the standard
     error envelope from `tech_doc.md` §8, request-ID middleware.
   - `app/core/config.py` — settings loaded from environment / `.env`
     (database URL, JWT secret, token lifetimes, CORS origins, timezone
     `Asia/Kolkata`, log level). Provide `.env.example`.
   - `app/core/db.py` — SQLAlchemy engine + session dependency.
   - `app/core/security.py` — password hash/verify, JWT encode/decode helpers
     (no endpoints wired to real users yet — a stub `get_current_user` /
     `require_role` dependency is enough).
   - `app/core/logging.py` — structured JSON logging with request IDs.
   - `GET /health` — liveness/readiness (checks DB connectivity).

6. Database setup:
   - Configure Alembic against the SQLAlchemy metadata.
   - Create the **initial migration** for the foundational tables only:
     `users`, `settings`, `audit_logs`, plus the enum types they need
     (`user_role`). Do **not** create customer/package/subscription tables in
     this phase.
   - Add a `scripts/` or Makefile target to run migrations and to seed the first
     ADMIN user + default `settings` rows from `tech_doc.md` §3.3 / §3.

7. Local development environment:
   - `docker-compose.yml` with a PostgreSQL 16 service for local dev and tests.
   - README section: how to install deps, start Postgres, run migrations, seed,
     run the server, run tests.

8. Testing skeleton:
   - `backend/tests/` with `conftest.py` providing a Postgres test database and
     per-test transaction rollback, plus a FastAPI `TestClient`/`httpx` fixture.
   - One passing smoke test for `GET /health`.
   - Wire `ruff`, `mypy`, and `pytest` so they all run clean.

9. CI:
   - GitHub Actions workflow: install via `uv`, `ruff check`, `mypy`, spin up
     Postgres, run `alembic upgrade head`, run `pytest`.

10. Deliverables check before finishing:
    - `uv run uvicorn app.main:app` starts and `GET /health` returns 200.
    - `alembic upgrade head` and `alembic downgrade base` both succeed on a clean
      database.
    - `pytest`, `ruff`, and `mypy` are green.
    - Update `README.md` with setup/run instructions.
    - Record anything still undecided at the end of this file under
      "Open questions".

# Status — Milestone 1 complete (2026-09-10)

Delivered on branch `backend-scaffold`:

- Repo restructured to `backend/`; prototype `tools.py` + `src/` removed.
- `uv` project: FastAPI, SQLAlchemy 2 (async, psycopg 3), Alembic, Argon2id,
  PyJWT, structlog; dev group ruff / mypy(strict) / pytest. `uv.lock` committed.
- App foundations: app factory, `/api/v1` mount, CORS, request-ID middleware,
  JSON logging, standard error envelope + handlers, `pydantic-settings` config
  (`HEALTHX_*`), async DB session dependency (DB session pinned to UTC).
- Auth: `POST /auth/login`, `/auth/refresh`, `GET /auth/me`, `POST /auth/logout`;
  Argon2id hashing, short access + rotating refresh JWT; `get_current_user`,
  `require_admin` / `require_staff` guards.
- User management (ADMIN): list (paginated) / create / get / update / deactivate.
- Models + initial migration `0001_foundation`: `users`, `settings`,
  `audit_logs`, `user_role` enum, `citext` extension. `timestamptz` columns.
- `audit_service.record()` infra; `USER_*` actions wired.
- `scripts/seed.py` — idempotent first ADMIN + default `settings` rows.
- `docker-compose.yml` (dev :5432 + test :5433 Postgres), `Makefile`.
- Tests: `tests/conftest.py` (real Postgres test DB, per-test rollback,
  ASGI client, user/token fixtures); 16 tests — health, request-id, readiness,
  auth flow, RBAC, user CRUD + audit, timezone invariant.
- CI: `.github/workflows/backend-ci.yml` — uv → ruff → mypy → Postgres →
  alembic up/down/up → pytest.
- Root + `backend/` READMEs.

Verified locally (PostgreSQL 16 via brew): ruff, mypy, `alembic upgrade head`
/ `downgrade base` / re-`upgrade`, seed (idempotent), 16/16 pytest, and a live
uvicorn run (login → me → create user → list, with an audit row written).

# Open questions / deferred

- **Refresh-token revocation**: `/auth/logout` is currently stateless (client
  discards tokens). A server-side denylist / rotation store is a v2 item
  (`tech_doc.md` §5.1) — revisit if session invalidation is needed sooner.
- **Password policy**: enforced as min-length 10 only. No complexity rules,
  rotation, or breach check (matches `tech_doc.md` §3.3). 2FA is v2.
- **Auth rate-limiting** (`tech_doc.md` §5.1): not implemented in M1 — belongs
  with a shared middleware/Redis story; add before production exposure.
- **Reserved email domains**: `EmailStr` rejects `.local` / `.test` / etc., so
  seed/default emails use `*.example.com`. Real deployments must use a routable
  domain.
- **Alembic autogenerate for enums**: `0001` is hand-written. When domain tables
  land, confirm autogenerate diffing of native enums is clean or keep authoring
  enum create/drop explicitly.
- **Local Postgres**: dev currently uses a brew `postgresql@16` instance with a
  data dir under the session scratchpad. For ongoing work, switch to
  `docker compose up -d` (in `backend/`) or `brew services start postgresql@16`.
