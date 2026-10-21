"""Import a validated airport master CSV into PostgreSQL."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

EXPECTED_COLUMNS = {
    "id", "ident", "type", "name", "latitude_deg", "longitude_deg",
    "elevation_ft", "iso_country", "iso_region", "municipality",
    "scheduled_service", "icao_code", "iata_code", "source",
    "build_date_utc", "master_scope",
}
UPSERT_SQL = """
INSERT INTO airports (
    source_name, source_airport_id, ident, airport_type, name,
    latitude_deg, longitude_deg, elevation_ft, iso_country, iso_region,
    municipality, scheduled_service, icao_code, iata_code,
    master_scope, source_build_date
)
VALUES (
    %(source_name)s, %(source_airport_id)s, %(ident)s, %(airport_type)s,
    %(name)s, %(latitude_deg)s, %(longitude_deg)s, %(elevation_ft)s,
    %(iso_country)s, %(iso_region)s, %(municipality)s,
    %(scheduled_service)s, %(icao_code)s, %(iata_code)s,
    %(master_scope)s, %(source_build_date)s
)
ON CONFLICT (source_name, source_airport_id) DO UPDATE SET
    ident = EXCLUDED.ident,
    airport_type = EXCLUDED.airport_type,
    name = EXCLUDED.name,
    latitude_deg = EXCLUDED.latitude_deg,
    longitude_deg = EXCLUDED.longitude_deg,
    elevation_ft = EXCLUDED.elevation_ft,
    iso_country = EXCLUDED.iso_country,
    iso_region = EXCLUDED.iso_region,
    municipality = EXCLUDED.municipality,
    scheduled_service = EXCLUDED.scheduled_service,
    icao_code = EXCLUDED.icao_code,
    iata_code = EXCLUDED.iata_code,
    master_scope = EXCLUDED.master_scope,
    source_build_date = EXCLUDED.source_build_date
"""
def _optional_text(value: object) -> str | None:
    """Convert pandas missing values and blank strings to None."""
    if pd.isna(value) or not str(value).strip():
        return None
    return str(value).strip()
def _optional_integer(value: object) -> int | None:
    """Convert an optional numeric value to an integer."""
    if pd.isna(value) or not str(value).strip():
        return None
    number = float(value)
    if not number.is_integer():
        raise ValueError(f"Expected a whole number, received {value!r}")
    return int(number)
def _optional_boolean(value: object) -> bool | None:
    """Convert common source boolean representations to bool or None."""
    text = _optional_text(value)
    if text is None:
        return None
    normalized = text.casefold()
    if normalized in {"yes", "true", "1"}:
        return True
    if normalized in {"no", "false", "0"}:
        return False
    raise ValueError(f"Unrecognized scheduled_service value: {value!r}")
def validate_airport_master(path: str | Path) -> list[dict]:
    """Read and validate CSV rows before any database write."""
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Airport master CSV not found: {csv_path}")
    frame = pd.read_csv(csv_path, dtype={"id": "string"}, low_memory=False)
    missing = sorted(EXPECTED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Airport master is missing columns: {missing}")
    if frame.empty:
        raise ValueError("Airport master contains no records.")
    if frame["id"].isna().any() or frame["id"].duplicated().any():
        raise ValueError("Airport master IDs must be present and unique.")
    records: list[dict] = []
    for row in frame.to_dict(orient="records"):
        source_name = _optional_text(row["source"])
        source_id = _optional_text(row["id"])
        name = _optional_text(row["name"])
        country = _optional_text(row["iso_country"])
        airport_type = _optional_text(row["type"])
        latitude = float(row["latitude_deg"])
        longitude = float(row["longitude_deg"])
        if not source_name or not source_id or not name or not country:
            raise ValueError("Source, ID, name, and country are required.")
        if not airport_type:
            raise ValueError(f"Airport {source_id} has no airport type.")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError(f"Airport {source_id} has invalid coordinates.")
        if country != "IN":
            raise ValueError(f"Airport {source_id} is outside the India scope.")
        build_date_text = _optional_text(row["build_date_utc"])
        try:
            build_date = date.fromisoformat(build_date_text) if build_date_text else None
        except ValueError as exc:
            raise ValueError(
                f"Airport {source_id} has an invalid build date."
            ) from exc
        records.append({
            "source_name": source_name,
            "source_airport_id": source_id,
            "ident": _optional_text(row["ident"]),
            "airport_type": airport_type,
            "name": name,
            "latitude_deg": latitude,
            "longitude_deg": longitude,
            "elevation_ft": _optional_integer(row["elevation_ft"]),
            "iso_country": country,
            "iso_region": _optional_text(row["iso_region"]),
            "municipality": _optional_text(row["municipality"]),
            "scheduled_service": _optional_boolean(row["scheduled_service"]),
            "icao_code": _optional_text(row["icao_code"]),
            "iata_code": _optional_text(row["iata_code"]),
            "master_scope": _optional_text(row["master_scope"]),
            "source_build_date": build_date,
        })
    return records
def import_airport_master(
    connection: psycopg.Connection,
    path: str | Path,
    *,
    dry_run: bool = True,
) -> dict[str, int | bool]:
    """Validate and import airport records atomically; dry-run is the default."""
    records = validate_airport_master(path)
    if dry_run:
        return {
            "dry_run": True,
            "records_validated": len(records),
            "records_upserted": 0,
        }
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO collection_runs (
                    run_type, status, records_received, records_accepted,
                    records_rejected, metadata
                )
                VALUES (
                    'airport_master_import', 'running', %s, 0, 0, %s
                )
                RETURNING run_id
                """,
                (
                    len(records),
                    Jsonb({"input_file": Path(path).name, "dry_run": False}),
                ),
            )
            run_id = cursor.fetchone()[0]
            cursor.executemany(UPSERT_SQL, records)
            upserted = len(records)
            cursor.execute(
                """
                UPDATE collection_runs
                SET status = 'succeeded',
                    finished_at = NOW(),
                    records_accepted = %s
                WHERE run_id = %s
                """,
                (upserted, run_id),
            )
    return {
        "dry_run": False,
        "records_validated": len(records),
        "records_upserted": upserted,
    }
