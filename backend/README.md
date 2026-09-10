# HealthX — Backend

FastAPI + PostgreSQL API for HealthX. Design reference: `../progress/tech_doc.md`.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker (for local PostgreSQL) — or any reachable PostgreSQL 16

## Setup

```bash
uv sync                       # install runtime + dev dependencies
docker compose up -d          # start dev DB (:5432) and test DB (:5433)
cp .env.example .env          # then edit secrets
uv run alembic upgrade head   # create the schema
uv run python -m scripts.seed # seed first ADMIN + default settings rows
```

The seed ADMIN's email/password come from `HEALTHX_SEED_ADMIN_*` in `.env`.

## Run

```bash
uv run uvicorn app.main:app --reload
# or: make run
```

- OpenAPI docs: http://localhost:8000/docs
- Liveness: `GET /api/v1/health`
- Readiness (checks DB): `GET /api/v1/health/ready`

## Auth

```bash
# login
curl -s localhost:8000/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"admin@healthx.local","password":"<seed password>"}'

# use the access_token
curl -s localhost:8000/api/v1/auth/me -H 'authorization: Bearer <access_token>'
```

Roles: `ADMIN`, `STAFF`. `/api/v1/users/*` is ADMIN-only (see `tech_doc.md` §5.2).

## Migrations

```bash
make migrate                       # alembic upgrade head
make downgrade                     # alembic downgrade -1
make revision m="add packages"     # autogenerate from model changes
```

`alembic/env.py` reads the database URL from app settings — no URL in
`alembic.ini`.

## Quality gates

```bash
make lint        # ruff
make typecheck   # mypy (strict) over app/ and scripts/
make test        # pytest against the :5433 test database
make check       # all three
```

Tests use a real PostgreSQL test database (`HEALTHX_DATABASE_URL`, default
`...:5433/healthx_test`) with per-test transaction rollback.

## Layout

```
app/
  main.py            FastAPI app factory
  core/              config, db session, security, logging, middleware, errors, deps
  models/            SQLAlchemy models (users, settings, audit_logs)
  schemas/           Pydantic request/response models
  api/v1/routers/    HTTP endpoints (health, auth, users)
  services/          business rules (transactional)
  repositories/      query helpers
  workers/           scheduled jobs (later phases)
alembic/             migrations
scripts/seed.py      idempotent seed
tests/               pytest
```
