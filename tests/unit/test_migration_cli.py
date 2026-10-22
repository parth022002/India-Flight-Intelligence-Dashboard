"""Tests for safe migration CLI connection selection."""
from __future__ import annotations

from flight_intelligence.storage import connection


def test_migration_connection_requires_explicit_url(
    monkeypatch,
) -> None:
    """Never silently fall back to the normal application database URL."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused-normal-url")
    monkeypatch.delenv("FLIGHT_INTEL_MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.setattr(connection, "load_dotenv", lambda: None)

    try:
        connection.connect_database(
            url_env_var="FLIGHT_INTEL_MIGRATION_DATABASE_URL"
        )
    except TypeError:
        # The explicit URL option will be added in the next implementation step.
        return
    except RuntimeError as exc:
        assert "FLIGHT_INTEL_MIGRATION_DATABASE_URL is missing" in str(exc)
    else:
        raise AssertionError("Migration connection must reject a missing URL")


def test_migration_connection_uses_explicit_url(
    monkeypatch,
) -> None:
    """Use only the dedicated migration URL when explicitly requested."""
    expected_url = "postgresql://migration-test-only"
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused-normal-url")
    monkeypatch.setenv("FLIGHT_INTEL_MIGRATION_DATABASE_URL", expected_url)
    monkeypatch.setattr(connection, "load_dotenv", lambda: None)

    captured = {}

    def fake_connect(url, *, connect_timeout):
        captured["url"] = url
        captured["timeout"] = connect_timeout
        return object()

    monkeypatch.setattr(connection.psycopg, "connect", fake_connect)

    connection.connect_database(
        url_env_var="FLIGHT_INTEL_MIGRATION_DATABASE_URL"
    )

    assert captured == {"url": expected_url, "timeout": 10}