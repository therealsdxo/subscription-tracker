"""Application settings, loaded from environment / .env.

All variables are prefixed ``HEALTHX_`` (see ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "ci", "dev", "prod"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HEALTHX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    env: Environment = "local"
    log_level: str = "INFO"
    timezone: str = "Asia/Kolkata"
    # ``NoDecode`` so a plain comma-separated env value is not JSON-parsed;
    # the validator below splits it. (The frontend talks to the API through a
    # same-origin server proxy, so CORS only matters for direct API clients.)
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # Database URL (psycopg 3 driver, e.g. postgresql+psycopg://user:pass@host/db).
    # Used as-is by the async API engine and by Alembic's sync engine.
    database_url: str = "postgresql+psycopg://healthx:healthx@localhost:5432/healthx"

    # Auth
    jwt_secret: str = "change-me-in-every-environment"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_minutes: int = 60 * 24 * 7

    # Seed helper
    seed_admin_email: str = "admin@healthx.example.com"
    seed_admin_password: str = "change-me-now-please"
    seed_admin_name: str = "HealthX Admin"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.env == "prod"

    @property
    def sync_database_url(self) -> str:
        """Same database, sync driver — used by Alembic."""
        return str(self.database_url)

    @property
    def async_database_url(self) -> str:
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
