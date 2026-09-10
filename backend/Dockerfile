# syntax=docker/dockerfile:1

# --- build ---------------------------------------------------------------
FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- runtime ------------------------------------------------------------
FROM python:3.13-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HEALTHX_ENV=prod

USER app
EXPOSE 8000

# ``PORT`` is set by the platform (ECS/App Runner); default 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
