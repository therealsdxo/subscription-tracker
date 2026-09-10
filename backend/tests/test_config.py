"""Settings parsing (app/core/config.py)."""

from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("http://localhost:3000", ["http://localhost:3000"]),
        (
            "http://localhost:3000, https://app.example.com",
            ["http://localhost:3000", "https://app.example.com"],
        ),
    ],
)
def test_cors_origins_accepts_plain_comma_separated_env(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    # A plain string env value must not be JSON-decoded (that used to crash).
    monkeypatch.setenv("HEALTHX_CORS_ORIGINS", raw)
    assert Settings().cors_origins == expected


def test_cors_origins_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HEALTHX_CORS_ORIGINS", raising=False)
    assert Settings().cors_origins == ["http://localhost:3000"]
