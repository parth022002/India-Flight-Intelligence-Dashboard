
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from flight_intelligence.collectors.adsb_orchestrator import run_adsb_collection
from flight_intelligence.storage.migrations import apply_migrations

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "sql" / "migrations"

AIRPORT_SELECT_COLUMNS = (
    "source_name source_airport_id ident airport_type name "
    "latitude_deg longitude_deg elevation_ft iso_country iso_region "
    "municipality scheduled_service icao_code iata_code master_scope "
    "source_build_date"
)
RUN_SELECT_COLUMNS = "run_id source_id run_type status"
RUN_UPDATE_COLUMNS = (
    "status finished_at records_received records_accepted "
    "records_rejected error_code error_summary"
)
SOURCE_SELECT_COLUMNS = "source_id source_name data_type license_status"
OBSERVATION_INSERT_COLUMNS = (
    "run_id source_id source_type source_record_key observed_at "
    "aircraft_id icao24 callsign latitude_deg longitude_deg altitude_ft "
    "on_ground assigned_airport_id assignment_distance_nm "
    "assignment_reason assignment_rule_version raw_payload"
)


def _grant_test_schema(conn: psycopg.Connection, schema: str) -> None:
    """Grant only the pipeline permissions needed on temporary test tables."""
    ident = sql.Identifier(schema)

    conn.execute(
        sql.SQL("GRANT USAGE ON SCHEMA {} TO ifi_pipeline_login").format(ident)
    )

    conn.execute(
        sql.SQL("GRANT INSERT, UPDATE ON TABLE {}.airports TO ifi_pipeline_writer")
        .format(ident)
    )
    conn.execute(
        sql.SQL("GRANT SELECT ({}) ON TABLE {}.airports TO ifi_pipeline_writer")
        .format(
            sql.SQL(", ").join(map(sql.Identifier, AIRPORT_SELECT_COLUMNS.split())),
            ident,
        )
    )

    conn.execute(
        sql.SQL(
            "GRANT INSERT ON TABLE {}.collection_runs TO ifi_pipeline_writer"
        ).format(ident)
    )
    conn.execute(
        sql.SQL("GRANT SELECT ({}) ON TABLE {}.collection_runs TO ifi_pipeline_writer")
        .format(
            sql.SQL(", ").join(map(sql.Identifier, RUN_SELECT_COLUMNS.split())),
            ident,
        )
    )
    conn.execute(
        sql.SQL("GRANT UPDATE ({}) ON TABLE {}.collection_runs TO ifi_pipeline_writer")
        .format(
            sql.SQL(", ").join(map(sql.Identifier, RUN_UPDATE_COLUMNS.split())),
            ident,
        )
    )

    conn.execute(
        sql.SQL("GRANT SELECT ({}) ON TABLE {}.data_sources TO ifi_pipeline_writer")
        .format(
            sql.SQL(", ").join(map(sql.Identifier, SOURCE_SELECT_COLUMNS.split())),
            ident,
        )
    )

    conn.execute(
        sql.SQL(
            "GRANT INSERT ({}) ON TABLE {}.adsb_observations TO ifi_pipeline_writer"
        ).format(
            sql.SQL(", ").join(
                map(sql.Identifier, OBSERVATION_INSERT_COLUMNS.split())
            ),
            ident,
        )
    )

    for sequence in (
        "airports_airport_id_seq",
        "collection_runs_run_id_seq",
        "adsb_observations_observation_id_seq",
    ):
        conn.execute(
            sql.SQL("GRANT USAGE ON SEQUENCE {}.{} TO ifi_pipeline_writer").format(
                ident, sql.Identifier(sequence)
            )
        )


@contextmanager
def restricted_test_database():
    """Create an isolated schema and connect using the restricted login."""
    admin_url = os.getenv("FLIGHT_INTEL_TEST_DATABASE_URL", "").strip()
    writer_url = os.getenv("FLIGHT_INTEL_WRITER_TEST_URL", "").strip()

    if not admin_url:
        pytest.skip("Set FLIGHT_INTEL_TEST_DATABASE_URL for isolated test setup.")
    if not writer_url:
        pytest.skip("Set FLIGHT_INTEL_WRITER_TEST_URL for restricted-role testing.")

    schema = f"ifi_restricted_test_{uuid4().hex[:12]}"

    with psycopg.connect(admin_url, connect_timeout=10, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

        try:
            with psycopg.connect(admin_url, connect_timeout=10) as setup:
                setup.execute(
                    sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
                )

                assert apply_migrations(setup, MIGRATIONS_DIR) == ["001"]

                setup.execute(
                    """
                    INSERT INTO data_sources
                        (source_name, source_url, data_type, license_status)
                    VALUES
                        ('adsb.lol', 'https://example.invalid/synthetic-test',
                         'adsb_api', 'approved')
                    """
                )
                _grant_test_schema(setup, schema)

            with psycopg.connect(writer_url, connect_timeout=10) as writer:
                role, database = writer.execute(
                    "SELECT current_user, current_database()"
                ).fetchone()

                assert role == "ifi_pipeline_login", (
                    f"Expected restricted role, got {role!r}"
                )
                assert database == "neondb", (
                    f"Unexpected test database: {database!r}"
                )

                writer.execute(
                    sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
                )

                active_schema = writer.execute(
                    "SELECT current_schema()"
                ).fetchone()[0]
                assert active_schema == schema, (
                    f"Expected schema {schema!r}, got {active_schema!r}"
                )

                visible_table = writer.execute(
                    "SELECT to_regclass('data_sources')"
                ).fetchone()[0]
                assert visible_table is not None, (
                    f"data_sources is not visible in schema {schema!r}"
                )

                yield writer, schema, admin_url
        finally:
            admin.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema)
                )
            )


def test_restricted_role_runs_orchestrator_and_cannot_read_or_delete_observations():
    with restricted_test_database() as (writer, schema, admin_url):
        source_id = writer.execute(
            "SELECT source_id FROM data_sources WHERE source_name = 'adsb.lol'"
        ).fetchone()[0]

        # Finish the transaction opened by the source lookup before running
        # the workflow, so the persistence transaction is not just a savepoint.
        writer.commit()

        client = type(
            "MockAdsbClient",
            (),
            {
                "config": type("Config", (), {"enabled": True})(),
                "fetch_aircraft": lambda self, endpoint: {
                    "aircraft": [
                        {
                            "hex": "a1b2c3",
                            "lat": 19.0896,
                            "lon": 72.8656,
                            "flight": "TEST123",
                            "alt_baro": 12000,
                        }
                    ]
                },
            },
        )()

        result = run_adsb_collection(
            writer, client, source_id=source_id, endpoint="/v0/test"
        )

        assert result["status"] == "succeeded"
        assert result["records_accepted"] == 1

        # Commit the workflow before verifying its data from another connection.
        writer.commit()

        # The restricted login must not be able to read or delete observations.
        for query, params in (
            (
                "SELECT observation_id FROM adsb_observations WHERE run_id = %s",
                (result["run_id"],),
            ),
            (
                "DELETE FROM adsb_observations WHERE run_id = %s",
                (result["run_id"],),
            ),
        ):
            with psycopg.connect(
                os.environ["FLIGHT_INTEL_WRITER_TEST_URL"],
                connect_timeout=10,
                autocommit=True,
            ) as restricted_check:
                restricted_check.execute(
                    sql.SQL("SET search_path TO {}").format(
                        sql.Identifier(schema)
                    )
                )

                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    restricted_check.execute(query, params)

        # Verify the persisted observation using the administrative connection.
        with psycopg.connect(admin_url, connect_timeout=10) as admin:
            admin.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
            )

            stored = admin.execute(
                """
                SELECT source_type, icao24, callsign
                FROM adsb_observations
                WHERE run_id = %s
                """,
                (result["run_id"],),
            ).fetchone()

            assert stored == ("live_poll", "a1b2c3", "TEST123")
