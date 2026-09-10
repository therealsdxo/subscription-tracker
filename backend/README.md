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
  -d '{"email":"admin@healthx.example.com","password":"<seed password>"}'

# use the access_token
curl -s localhost:8000/api/v1/auth/me -H 'authorization: Bearer <access_token>'
```

Roles: `ADMIN`, `STAFF`. `/api/v1/users/*` is ADMIN-only (see `tech_doc.md` §5.2).

## Endpoints

| Area | Endpoints | Access |
|---|---|---|
| Health | `GET /health`, `GET /health/ready` | public |
| Auth | `POST /auth/login` · `/auth/refresh` · `/auth/logout`, `GET /auth/me` | public / bearer |
| Users | `GET/POST /users`, `GET/PATCH /users/{id}`, `POST /users/{id}/deactivate` | ADMIN |
| Packages | `GET /packages` (`?status=`), `GET /packages/{id}` | STAFF |
| | `POST /packages`, `PATCH /packages/{id}`, `POST /packages/{id}/activate` · `/deactivate`, `DELETE /packages/{id}` | ADMIN |
| Customers | `GET /customers` (`?q= &phone= &code= &is_active=`), `POST /customers`, `GET /customers/{id}`, `PATCH /customers/{id}` | STAFF |
| | `POST /customers/{id}/deactivate` · `/reactivate` | ADMIN |
| Addresses | `GET/POST /customers/{id}/addresses`, `PATCH/DELETE /customers/{id}/addresses/{aid}` | STAFF |

Packages compute `final_price = base_price + tax_amount` and are assigned a
`PKG-#####` code; customers get a `CUST-######` code (prefix/width from the
`settings` table). Customer create requires ≥ 1 address; a possible-duplicate
name returns `warnings[]` in the `{data, warnings}` envelope but still succeeds.
Customers are only ever soft-deleted.

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
  models/            SQLAlchemy models (users, settings, audit_logs, packages,
                     customers, customer_addresses, code sequences)
  schemas/           Pydantic request/response models
  api/v1/routers/    HTTP endpoints (health, auth, users, packages, customers)
  services/          business rules (transactional)
  repositories/      query helpers
  workers/           scheduled jobs (later phases)
alembic/             migrations
scripts/seed.py      idempotent seed
tests/               pytest
```
