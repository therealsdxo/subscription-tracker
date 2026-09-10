.PHONY: help install db-up db-down migrate downgrade revision seed run lint typecheck test check

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime + dev dependencies
	uv sync

db-up:  ## Start local Postgres (dev + test)
	docker compose up -d

db-down:  ## Stop local Postgres
	docker compose down

migrate:  ## Apply all migrations
	uv run alembic upgrade head

downgrade:  ## Roll back the last migration
	uv run alembic downgrade -1

revision:  ## Autogenerate a migration: make revision m="add packages"
	uv run alembic revision --autogenerate -m "$(m)"

seed:  ## Seed the first ADMIN user + default settings
	uv run python -m scripts.seed

run:  ## Run the API with autoreload
	uv run uvicorn app.main:app --reload

lint:  ## Ruff
	uv run ruff check .

typecheck:  ## mypy
	uv run mypy app scripts

test:  ## pytest
	uv run pytest

check: lint typecheck test  ## Lint + typecheck + test
