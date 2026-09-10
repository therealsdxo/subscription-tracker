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
| `frontend/` | Next.js web app *(added in a later phase)* |
| `infra/` | Terraform for AWS *(added in a later phase)* |

## Status

Milestone 1 (Foundation) — backend scaffold: config, DB + Alembic, `users`,
auth (login / refresh / RBAC), audit-log infrastructure, `settings`, health
checks, CI. See `progress/tech_doc.md` §16 for the full roadmap.

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
