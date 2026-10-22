from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from flight_intelligence.collectors.adsb_orchestrator import run_adsb_collection
from flight_intelligence.storage.migrations import apply_migrations

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "sql" / "migrations"


@contextmanager
def isolated_database():
    database_url = os.getenv("FLIGHT_INTEL_TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("Set FLIGHT_INTEL_TEST_DATABASE_URL to run this PostgreSQL test.")

    schema_name = f"flight_intel_orchestrator_test_{uuid4().hex[:12]}"

    with psycopg.connect(
        database_url, connect_timeout=10, autocommit=True
    ) as admin:
        admin.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name))
        )
        try:
            with psycopg.connect(database_url, connect_timeout=10) as conn:
                conn.execute(
                    sql.SQL("SET search_path TO {}").format(
                        sql.Identifier(schema_name)
                    )
                )
                assert apply_migrations(conn, MIGRATIONS_DIR) == ["001"]
                yield conn
        finally:
            admin.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema_name)
                )
            )


def test_orchestrator_persists_mocked_collection_and_finalizes_run():
    with isolated_database() as conn:
        source_id = conn.execute(
            """
            INSERT INTO data_sources
                (source_name, source_url, data_type, license_status)
            VALUES (%s, %s, 'adsb_api', 'approved')
            RETURNING source_id
            """,
            (
                "adsb.lol",
                "https://example.invalid/synthetic-test-data",
            ),
        ).fetchone()[0]

        client = MagicMock()
        client.config.enabled = True
        client.fetch_aircraft.return_value = {
            "aircraft": [
                {
                    "hex": "a1b2c3",
                    "lat": 19.0896,
                    "lon": 72.8656,
                    "flight": "TEST123",
                    "alt_baro": 12000,
                }
            ]
        }

        result = run_adsb_collection(
            conn,
            client,
            source_id=source_id,
            endpoint="/v0/test",
        )

        assert result["status"] == "succeeded"
        assert result["records_accepted"] == 1
        client.fetch_aircraft.assert_called_once_with("/v0/test")

        run = conn.execute(
            """
            SELECT run_id, status, records_received, records_accepted
            FROM collection_runs
            WHERE source_id = %s
            """,
            (source_id,),
        ).fetchone()

        assert run == (result["run_id"], "succeeded", 1, 1)

        observation = conn.execute(
            """
            SELECT source_type, icao24, callsign
            FROM adsb_observations
            WHERE run_id = %s
            """,
            (result["run_id"],),
        ).fetchone()

        assert observation == ("live_poll", "a1b2c3", "TEST123")