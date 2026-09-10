# HealthX

Centralized meal-subscription management for a healthy meal-delivery business —
the single source of truth for customers, meal packages, subscriptions,
deliveries, and payments.

## Repository layout

| Path | Contents |
|---|---|
| `project.md` | Original project brief |
| `progress/` | Planning docs — questionnaire, `tech_doc.md` (v1 technical design), phase plans |
| `backend/` | FastAPI + PostgreSQL API service (see `backend/README.md`) |
| `infra/` | Terraform for the AWS deployment (see `infra/README.md`) |
| `frontend/` | Next.js web app *(not started)* |

## Status

Backend **v1 complete** (Milestones 1–6, `progress/tech_doc.md` §16):

- **M1** Foundation — config, DB + Alembic, users, auth (login/refresh/RBAC), audit log, settings, health, CI
- **M2** Customers & packages — CRUD, soft delete, addresses, codes, bounds
- **M3** Subscriptions — snapshot, calendar-day expiry, one-ACTIVE/PENDING, pause/resume/extend/cancel/renew, meal adjustments, expiry job
- **M4** Deliveries — daily generation (Tuesday/holiday/skip aware), outcome recording with a row lock, reversal
- **M5** Payments — installments, derived `payment_status` / `outstanding_amount`, refunds, dues filter
- **M6** Dashboard summary, CSV export, CSV customer import, login rate-limiting, `Dockerfile`, `infra/` Terraform (AWS)

The Next.js frontend is not started.

## Quick start (backend)

```bash
cd backend
uv sync
docker compose up -d            # local + test Postgres
cp .env.example .env
uv run alembic upgrade head
uv run python -m scripts.seed   # first ADMIN user + default settings
uv run uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs · health at
http://localhost:8000/api/v1/health
