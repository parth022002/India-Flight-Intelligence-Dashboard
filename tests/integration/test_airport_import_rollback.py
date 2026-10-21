from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from flight_intelligence.storage.airport_import import import_airport_master
from flight_intelligence.storage.migrations import apply_migrations

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "sql" / "migrations"
AIRPORT_CSV = PROJECT_ROOT / "data" / "processed" / "india_airport_master.csv"


def test_airport_import_rolls_back_after_database_failure() -> None:
    """Verify a failed import leaves no partial rows in an isolated schema."""
    database_url = os.getenv("FLIGHT_INTEL_TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("Set FLIGHT_INTEL_TEST_DATABASE_URL to run the Neon integration test.")
    if not AIRPORT_CSV.is_file():
        pytest.fail(f"Airport master CSV is missing: {AIRPORT_CSV}")
    schema_name = f"flight_intel_test_{uuid4().hex[:12]}"
    # Never fall back to DATABASE_URL; require the explicit test variable.
    with psycopg.connect(database_url, connect_timeout=10, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
        try:
            with psycopg.connect(
                database_url,
                connect_timeout=10,
            ) as conn:
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema_name)))
                applied = apply_migrations(conn, MIGRATIONS_DIR)
                assert applied == ["001"]
                conn.execute(
                    """
                    ALTER TABLE airports
                    ADD CONSTRAINT force_rollback_test CHECK (FALSE)
                    """
                )
                with pytest.raises(psycopg.errors.CheckViolation):
                    import_airport_master(conn, AIRPORT_CSV, dry_run=False)
                run_count = conn.execute("SELECT COUNT(*) FROM collection_runs").fetchone()[0]
                airport_count = conn.execute("SELECT COUNT(*) FROM airports").fetchone()[0]
                assert run_count == 0
                assert airport_count == 0
        finally:
            admin.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name))
            )
