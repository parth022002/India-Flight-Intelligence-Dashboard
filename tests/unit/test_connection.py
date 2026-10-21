"""Tests for PostgreSQL connection helpers."""
from __future__ import annotations

import pytest

from flight_intelligence.storage.connection import connect_database


def test_connect_database_rejects_nonpositive_timeout() -> None:
    """Reject invalid timeouts before loading credentials or connecting."""
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        connect_database(timeout_seconds=0)
def test_connect_database_rejects_negative_timeout() -> None:
    """Reject negative connection timeouts."""
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        connect_database(timeout_seconds=-1)
def test_connect_database_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise a safe error when DATABASE_URL is not configured."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        "flight_intelligence.storage.connection.load_dotenv",
        lambda: None,
    )
    with pytest.raises(
        RuntimeError,
        match="DATABASE_URL is missing",
    ):
        connect_database()
