"""Transactional persistence for normalized ADS-B observations."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

OBSERVATION_FIELDS = (
    "source_record_key",
    "observed_at",
    "aircraft_id",
    "icao24",
    "callsign",
    "latitude_deg",
    "longitude_deg",
    "altitude_ft",
    "on_ground",
    "assigned_airport_id",
    "assignment_distance_nm",
    "assignment_reason",
    "assignment_rule_version",
    "raw_payload",
)
INSERT_OBSERVATION_SQL = """
INSERT INTO adsb_observations (
    run_id, source_id, source_type, source_record_key, observed_at,
    aircraft_id, icao24, callsign, latitude_deg, longitude_deg,
    altitude_ft, on_ground, assigned_airport_id, assignment_distance_nm,
    assignment_reason, assignment_rule_version, raw_payload
)
VALUES (
    %(run_id)s, %(source_id)s, %(source_type)s, %(source_record_key)s,
    %(observed_at)s, %(aircraft_id)s, %(icao24)s, %(callsign)s,
    %(latitude_deg)s, %(longitude_deg)s, %(altitude_ft)s, %(on_ground)s,
    %(assigned_airport_id)s, %(assignment_distance_nm)s,
    %(assignment_reason)s, %(assignment_rule_version)s, %(raw_payload)s
)
"""
FINALIZE_RUN_SQL = """
UPDATE collection_runs
SET status = %(status)s,
    finished_at = NOW(),
    records_received = %(records_received)s,
    records_accepted = %(records_accepted)s,
    records_rejected = %(records_rejected)s,
    error_code = %(error_code)s,
    error_summary = %(error_summary)s
WHERE run_id = %(run_id)s
  AND status = 'running'
"""
def _positive_id(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value
def _optional_finite_number(value: object, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric or None")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number
def _validate_record(
    record: Mapping[str, Any],
    *,
    run_id: int,
    source_id: int,
    source_type: str,
    include_raw_payload: bool,
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("each observation must be a mapping")
    record_run_id = _positive_id(record.get("run_id"), "record.run_id")
    record_source_id = _positive_id(record.get("source_id"), "record.source_id")
    if record_run_id != run_id or record_source_id != source_id:
        raise ValueError("observation run_id/source_id does not match persistence arguments")
    if record.get("source_type") != source_type:
        raise ValueError("observation source_type does not match persistence arguments")
    key = record.get("source_record_key")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("source_record_key must be a non-empty string")
    latitude = _optional_finite_number(record.get("latitude_deg"), "latitude_deg")
    longitude = _optional_finite_number(record.get("longitude_deg"), "longitude_deg")
    if latitude is not None and not -90 <= latitude <= 90:
        raise ValueError("latitude_deg is out of range")
    if longitude is not None and not -180 <= longitude <= 180:
        raise ValueError("longitude_deg is out of range")
    altitude = _optional_finite_number(record.get("altitude_ft"), "altitude_ft")
    distance = _optional_finite_number(
        record.get("assignment_distance_nm"), "assignment_distance_nm"
    )
    if distance is not None and distance < 0:
        raise ValueError("assignment_distance_nm cannot be negative")
    observed_at = record.get("observed_at")
    if observed_at is not None and not isinstance(observed_at, datetime):
        raise ValueError("observed_at must be a datetime or None")
    on_ground = record.get("on_ground")
    if on_ground is not None and not isinstance(on_ground, bool):
        raise ValueError("on_ground must be a boolean or None")
    assigned_airport_id = record.get("assigned_airport_id")
    if assigned_airport_id is not None:
        assigned_airport_id = _positive_id(
            assigned_airport_id, "assigned_airport_id"
        )
    values = {
        "run_id": run_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_record_key": key.strip(),
        "observed_at": observed_at,
        "aircraft_id": record.get("aircraft_id"),
        "icao24": record.get("icao24"),
        "callsign": record.get("callsign"),
        "latitude_deg": latitude,
        "longitude_deg": longitude,
        "altitude_ft": altitude,
        "on_ground": on_ground,
        "assigned_airport_id": assigned_airport_id,
        "assignment_distance_nm": distance,
        "assignment_reason": record.get("assignment_reason"),
        "assignment_rule_version": record.get("assignment_rule_version"),
        "raw_payload": (
            Jsonb(dict(record["raw_payload"]))
            if include_raw_payload and record.get("raw_payload") is not None
            else None
        ),
    }
    for field in ("aircraft_id", "icao24", "callsign",
                  "assignment_reason", "assignment_rule_version"):
        value = values[field]
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field} must be a string or None")
    return values
def persist_adsb_observations(
    connection: psycopg.Connection,
    observations: Sequence[Mapping[str, Any]],
    *,
    run_id: int,
    source_id: int,
    source_type: str = "live_poll",
    records_received: int | None = None,
    records_rejected: int = 0,
    include_raw_payload: bool = False,
) -> dict[str, int | str]:
    """Insert observations and finalize an existing collection run atomically.
    The run must already exist, be running, and match the supplied source and
    run type. This function performs no network requests and creates no run.
    """
    run_id = _positive_id(run_id, "run_id")
    source_id = _positive_id(source_id, "source_id")
    if source_type not in {"live_poll", "archive_sample"}:
        raise ValueError("source_type must be live_poll or archive_sample")
    if not isinstance(include_raw_payload, bool):
        raise ValueError("include_raw_payload must be a boolean")
    if isinstance(records_rejected, bool) or not isinstance(records_rejected, int):
        raise ValueError("records_rejected must be a nonnegative integer")
    if records_rejected < 0:
        raise ValueError("records_rejected must be a nonnegative integer")
    validated = [
        _validate_record(
            record,
            run_id=run_id,
            source_id=source_id,
            source_type=source_type,
            include_raw_payload=include_raw_payload,
        )
        for record in observations
    ]
    received = len(validated) + records_rejected if records_received is None else records_received
    if isinstance(received, bool) or not isinstance(received, int) or received < 0:
        raise ValueError("records_received must be a nonnegative integer")
    if received != len(validated) + records_rejected:
        raise ValueError("records_received must equal accepted plus rejected records")
    keys = [record["source_record_key"] for record in validated]
    if len(keys) != len(set(keys)):
        raise ValueError("source_record_key values must be unique within this batch")
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT run_type, status, source_id
                FROM collection_runs
                WHERE run_id = %s
                FOR UPDATE
                """,
                (run_id,),
            )
            run = cursor.fetchone()
            if run is None:
                raise ValueError("collection run does not exist")
            run_type, status, run_source_id = run
            if status != "running":
                raise ValueError("collection run must be running")
            if run_type != source_type:
                raise ValueError("source_type does not match collection run type")
            if run_source_id != source_id:
                raise ValueError("source_id does not match collection run source")
            cursor.executemany(INSERT_OBSERVATION_SQL, validated)
            final_status = "partial" if records_rejected else "succeeded"
            cursor.execute(
                FINALIZE_RUN_SQL,
                {
                    "run_id": run_id,
                    "status": final_status,
                    "records_received": received,
                    "records_accepted": len(validated),
                    "records_rejected": records_rejected,
                    "error_code": "records_rejected" if records_rejected else None,
                    "error_summary": (
                        f"{records_rejected} records rejected during validation"
                        if records_rejected
                        else None
                    ),
                },
            )
            if cursor.rowcount != 1:
                raise RuntimeError("collection run could not be finalized")
    return {
        "run_id": run_id,
        "status": final_status,
        "records_received": received,
        "records_accepted": len(validated),
        "records_rejected": records_rejected,
    }
