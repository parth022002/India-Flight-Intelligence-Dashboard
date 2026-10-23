
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from flight_intelligence.collectors.adsb_orchestrator import run_adsb_collection
from flight_intelligence.storage.airport_import import import_airport_master
from flight_intelligence.storage.migrations import apply_migrations

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "sql" / "migrations"
VALID_ENDPOINT = "/v2/lat/19.0760/lon/72.8777/dist/50"
AIRPORT_CSV = PROJECT_ROOT / "data" / "processed" / "india_airport_master.csv"

AIRPORT_SELECT_COLUMNS = (
    "source_name source_airport_id ident airport_type name "
    "latitude_deg longitude_deg elevation_ft iso_country iso_region "
    "municipality scheduled_service icao_code iata_code master_scope "
    "source_build_date"
)
AIRPORT_UPDATE_COLUMNS = (
    "ident airport_type name latitude_deg longitude_deg elevation_ft "
    "iso_country iso_region municipality scheduled_service icao_code "
    "iata_code master_scope source_build_date"
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

    # Airport master import: INSERT plus narrowly scoped UPDATE.
    conn.execute(
        sql.SQL("GRANT INSERT ON TABLE {}.airports TO ifi_pipeline_writer").format(
            ident
        )
    )
    conn.execute(
        sql.SQL("REVOKE UPDATE ON TABLE {}.airports FROM ifi_pipeline_writer").format(
            ident
        )
    )
    conn.execute(
        sql.SQL("GRANT UPDATE ({}) ON TABLE {}.airports TO ifi_pipeline_writer").format(
            sql.SQL(", ").join(
                map(sql.Identifier, AIRPORT_UPDATE_COLUMNS.split())
            ),
            ident,
        )
    )
    conn.execute(
        sql.SQL("GRANT SELECT ({}) ON TABLE {}.airports TO ifi_pipeline_writer").format(
            sql.SQL(", ").join(map(sql.Identifier, AIRPORT_SELECT_COLUMNS.split())),
            ident,
        )
    )

    # Collection run creation and narrowly scoped finalization.
    conn.execute(
        sql.SQL(
            "GRANT INSERT ON TABLE {}.collection_runs TO ifi_pipeline_writer"
        ).format(ident)
    )
    conn.execute(
        sql.SQL(
            "GRANT SELECT ({}) ON TABLE {}.collection_runs TO ifi_pipeline_writer"
        ).format(
            sql.SQL(", ").join(map(sql.Identifier, RUN_SELECT_COLUMNS.split())),
            ident,
        )
    )
    conn.execute(
        sql.SQL(
            "GRANT UPDATE ({}) ON TABLE {}.collection_runs TO ifi_pipeline_writer"
        ).format(
            sql.SQL(", ").join(map(sql.Identifier, RUN_UPDATE_COLUMNS.split())),
            ident,
        )
    )

    # Source verification for the ADS-B orchestrator.
    conn.execute(
        sql.SQL(
            "GRANT SELECT ({}) ON TABLE {}.data_sources TO ifi_pipeline_writer"
        ).format(
            sql.SQL(", ").join(map(sql.Identifier, SOURCE_SELECT_COLUMNS.split())),
            ident,
        )
    )

    # ADS-B observations: insertion only, without direct read/delete access.
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

    # Identity sequences used by the importer and collector.
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

                active_schema = writer.execute("SELECT current_schema()").fetchone()[0]
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
    """The restricted login can collect ADS-B but cannot read/delete observations."""
    with restricted_test_database() as (writer, schema, admin_url):
        source_id = writer.execute(
            "SELECT source_id FROM data_sources WHERE source_name = 'adsb.lol'"
        ).fetchone()[0]
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
            writer, client, source_id=source_id, endpoint=VALID_ENDPOINT
        )

        assert result["status"] == "succeeded"
        assert result["records_accepted"] == 1
        writer.commit()

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
                    sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
                )
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    restricted_check.execute(query, params)

        # Verify stored data with the administrative connection.
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


def test_restricted_role_can_update_only_approved_airport_columns():
    """The writer can update only the airport UPSERT columns."""
    with restricted_test_database() as (writer, schema, _admin_url):
        allowed_columns = set(AIRPORT_UPDATE_COLUMNS.split())

        rows = writer.execute(
            """
            SELECT column_name,
                   has_column_privilege(
                       current_user,
                       %s,
                       column_name,
                       'UPDATE'
                   )
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = 'airports'
            """,
            (f"{schema}.airports", schema),
        ).fetchall()

        actual_allowed = {
            column for column, can_update in rows if can_update
        }
        assert actual_allowed == allowed_columns

        # These statements should fail at permission checking, even with no
        # matching rows. Roll back after each expected permission error.
        for column in ("airport_id", "imported_at"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                writer.execute(
                    sql.SQL("UPDATE {}.airports SET {} = {} WHERE FALSE").format(
                        sql.Identifier(schema),
                        sql.Identifier(column),
                        sql.SQL("DEFAULT"),
                    )
                )
            writer.rollback()


def test_restricted_role_successfully_imports_airport_master():
    """The restricted writer can import airports with narrowed UPDATE grants."""
    if not AIRPORT_CSV.is_file():
        pytest.fail(f"Airport master CSV is missing: {AIRPORT_CSV}")

    with restricted_test_database() as (writer, schema, admin_url):
        # Finish the fixture's initial lookup transaction before starting import.
        writer.commit()

        result = import_airport_master(
            writer,
            AIRPORT_CSV,
            dry_run=False,
        )

        assert result == {
            "dry_run": False,
            "records_validated": 320,
            "records_upserted": 320,
        }

        # The importer should have committed its transaction successfully.
        with psycopg.connect(admin_url, connect_timeout=10) as admin:
            admin.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
            )

            airport_count = admin.execute(
                "SELECT COUNT(*) FROM airports"
            ).fetchone()[0]
            assert airport_count == 320

            run = admin.execute(
                """
                SELECT run_type, status, records_received, records_accepted
                FROM collection_runs
                ORDER BY run_id DESC
                LIMIT 1
                """
            ).fetchone()

            assert run == ("airport_master_import", "succeeded", 320, 320)

            # imported_at is database-managed and should remain populated.
            imported_at_count = admin.execute(
                "SELECT COUNT(*) FROM airports WHERE imported_at IS NOT NULL"
            ).fetchone()[0]
            assert imported_at_count == 320
