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
| Subscriptions | `GET /subscriptions` (`?status= &customer_id= &expiring= &dues=`), `POST /subscriptions`, `GET /subscriptions/{id}`, `PATCH /subscriptions/{id}`, `GET /subscriptions/{id}/events` · `/deliveries` · `/skips` · `/payments` · `/refunds` | STAFF |
| | `POST /subscriptions/{id}/pause` · `/resume` · `/renew` · `/skips` · `/payments`, `DELETE .../skips/{id}` | STAFF |
| | `POST /subscriptions/{id}/extend` · `/cancel` · `/meal-adjustments` · `/refunds` | ADMIN |
| Deliveries | `GET /deliveries?date=` (`&status= &area= &time_slot= &subscription_id=`), `POST /deliveries/generate`, `PATCH /deliveries/{id}`, `POST /deliveries/{id}/reverse` | STAFF |
| Holidays | `GET /holidays` (`?start= &end=`) | STAFF |
| | `POST /holidays`, `DELETE /holidays/{id}` | ADMIN |
| Payments | `GET /payments` (`?subscription_id= &customer_id= &method= &date_from= &date_to=`), `GET /payments/{id}` | STAFF |

Packages compute `final_price = base_price + tax_amount` and are assigned a
`PKG-#####` code; customers get a `CUST-######` code (prefix/width from the
`settings` table). Customer create requires ≥ 1 address; a possible-duplicate
name returns `warnings[]` in the `{data, warnings}` envelope but still succeeds.
Customers are only ever soft-deleted.

**Subscriptions** snapshot the package (name/meals/validity/prices), the chosen
delivery address, and the dietary preference at creation. `expected_end_date =
start_date + validity_days` (calendar days). At most one `ACTIVE` subscription
per customer — a second is queued `PENDING` and activates when the first ends.
Pause→resume pushes the expiry out by the paused days; ADMIN extend / cancel /
meal-adjust are audited. Status is stored but re-checked on read; a nightly
sweep keeps it fresh:

```bash
uv run python -m scripts.run_expiry_job   # activate due PENDING, expire overdue
```

**Deliveries** are generated per day from due `ACTIVE` subscriptions
(`POST /deliveries/generate {date}`, idempotent). Nothing is generated on the
weekly closed day (`closed_weekday` setting, default Tuesday) or a `holidays`
date. Recording a `DELIVERED` outcome decrements `meals_consumed` (auto-
`COMPLETED` at zero) under a row lock; `POST /deliveries/{id}/reverse` restores
the exact amount and re-opens the delivery. Adding a holiday or a planned skip
cancels deliveries already scheduled for those dates.

**Payments** are recorded against a subscription (which owes its snapshotted
`final_price`); multiple installments are allowed. `payment_status` /
`total_paid` / `net_paid` / `outstanding_amount` / `suggested_refund` are
**derived** (never stored) and appear on every subscription response.
`outstanding_amount = max(final_price − (Σ payments − Σ refunds), 0)`. Refunds
are ADMIN-only, require a reason, and cannot exceed the net amount paid; there is
no automatic proration (`suggested_refund` is guidance only). Payment state
never blocks activation or delivery recording. `GET /subscriptions?dues=true`
lists subscriptions with an outstanding balance.

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
                     customers/addresses, subscriptions/events/meal_adjustments,
                     deliveries/planned_skips/holidays, payments/refunds,
                     code sequences)
  schemas/           Pydantic request/response models
  api/v1/presenters.py  enrich subscriptions with the derived payment view
  api/v1/routers/    HTTP endpoints (health, auth, users, packages, customers,
                     subscriptions, deliveries, holidays, payments)
  services/          business rules (transactional)
  repositories/      query helpers
  workers/           expiry_job — daily activate/expire sweep
alembic/             migrations
scripts/             seed.py, run_expiry_job.py
tests/               pytest
```
