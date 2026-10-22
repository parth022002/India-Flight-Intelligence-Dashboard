from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from flight_intelligence.storage.adsb_persistence import persist_adsb_observations
from flight_intelligence.storage.migrations import apply_migrations

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "sql" / "migrations"


def _create_test_source_and_run(conn: psycopg.Connection) -> tuple[int, int]:
    source_id = conn.execute(
        """
        INSERT INTO data_sources
            (source_name, source_url, data_type, license_status)
        VALUES
            (%s, %s, %s, %s)
        RETURNING source_id
        """,
        (
            f"synthetic_adsb_test_{uuid4().hex}",
            "https://example.invalid/synthetic-test-data",
            "adsb_api",
            "not_reviewed",
        ),
    ).fetchone()[0]
    run_id = conn.execute(
        """
        INSERT INTO collection_runs (source_id, run_type, status)
        VALUES (%s, 'live_poll', 'running')
        RETURNING run_id
        """,
        (source_id,),
    ).fetchone()[0]
    return source_id, run_id


def _synthetic_observation(source_id: int, run_id: int) -> dict:
    return {
        "run_id": run_id,
        "source_id": source_id,
        "source_type": "live_poll",
        "source_record_key": f"synthetic-{uuid4().hex}",
        "observed_at": None,
        "aircraft_id": None,
        "icao24": "a1b2c3",
        "callsign": "TEST123",
        "latitude_deg": 19.0896,
        "longitude_deg": 72.8656,
        "altitude_ft": 12000.0,
        "on_ground": False,
        "assigned_airport_id": None,
        "assignment_distance_nm": None,
        "assignment_reason": None,
        "assignment_rule_version": None,
        "raw_payload": None,
    }


@contextmanager
def _isolated_database():
    database_url = os.getenv("FLIGHT_INTEL_TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("Set FLIGHT_INTEL_TEST_DATABASE_URL to run the Neon integration test.")
    schema_name = f"flight_intel_adsb_test_{uuid4().hex[:12]}"
    with psycopg.connect(database_url, connect_timeout=10, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
        try:
            with psycopg.connect(database_url, connect_timeout=10) as conn:
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema_name)))
                applied = apply_migrations(conn, MIGRATIONS_DIR)
                assert applied == ["001"]
                yield conn
        finally:
            admin.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name))
            )


def test_adsb_persistence_inserts_observation_and_finalizes_run() -> None:
    with _isolated_database() as conn:
        source_id, run_id = _create_test_source_and_run(conn)
        observation = _synthetic_observation(source_id, run_id)
        result = persist_adsb_observations(
            conn,
            [observation],
            run_id=run_id,
            source_id=source_id,
        )
        assert result == {
            "run_id": run_id,
            "status": "succeeded",
            "records_received": 1,
            "records_accepted": 1,
            "records_rejected": 0,
        }
        stored = conn.execute(
            """
            SELECT source_type, source_record_key, icao24, callsign
            FROM adsb_observations
            WHERE run_id = %s
            """,
            (run_id,),
        ).fetchone()
        assert stored == (
            "live_poll",
            observation["source_record_key"],
            "a1b2c3",
            "TEST123",
        )
        run = conn.execute(
            "SELECT status, records_accepted FROM collection_runs WHERE run_id = %s",
            (run_id,),
        ).fetchone()
        assert run == ("succeeded", 1)


def test_adsb_persistence_rolls_back_observation_when_finalization_fails() -> None:
    with _isolated_database() as conn:
        source_id, run_id = _create_test_source_and_run(conn)
        observation = _synthetic_observation(source_id, run_id)
        conn.execute(
            """
            ALTER TABLE collection_runs
            ADD CONSTRAINT force_adsb_finalize_failure
            CHECK (status <> 'succeeded')
            """
        )
        with pytest.raises(psycopg.errors.CheckViolation):
            persist_adsb_observations(
                conn,
                [observation],
                run_id=run_id,
                source_id=source_id,
            )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM adsb_observations WHERE run_id = %s",
                (run_id,),
            ).fetchone()[0]
            == 0
        )
        run = conn.execute(
            "SELECT status, records_accepted FROM collection_runs WHERE run_id = %s",
            (run_id,),
        ).fetchone()
        assert run == ("running", 0)
