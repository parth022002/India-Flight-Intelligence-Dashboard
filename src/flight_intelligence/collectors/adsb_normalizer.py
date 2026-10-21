"""Normalize validated ADS-B payloads into database-ready observation records."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from flight_intelligence.validation.adsb import validate_adsb_payload

ICAO24_PATTERN = re.compile(r"^[0-9a-f]{6}$")
def _optional_float(value: Any) -> float | None:
    """Return a finite float, or None for missing/invalid values."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number
def _optional_text(value: Any) -> str | None:
    """Trim optional text fields and convert empty strings to None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
def normalize_adsb_payload(
    payload: Mapping[str, Any],
    *,
    run_id: int,
    source_id: int,
    source_type: str = "live_poll",
    include_raw_payload: bool = False,
) -> list[dict[str, Any]]:
    """Convert a validated ADS-B payload to database observation records.
    Timestamps are left null unless a documented source timestamp mapping is
    added. Airport assignment is deferred to the Stage 5 assignment process.
    """
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id < 1:
        raise ValueError("run_id must be a positive integer")
    if isinstance(source_id, bool) or not isinstance(source_id, int) or source_id < 1:
        raise ValueError("source_id must be a positive integer")
    if source_type not in {"live_poll", "archive_sample"}:
        raise ValueError("source_type must be live_poll or archive_sample")
    errors = validate_adsb_payload(payload)
    if errors:
        raise ValueError(f"invalid ADS-B payload ({len(errors)} validation errors)")
    records: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for index, aircraft in enumerate(payload["aircraft"]):
        raw_icao24 = _optional_text(aircraft.get("hex"))
        icao24 = raw_icao24.lower() if raw_icao24 else None
        if icao24 and not ICAO24_PATTERN.fullmatch(icao24):
            icao24 = None
        latitude = _optional_float(aircraft.get("lat"))
        longitude = _optional_float(aircraft.get("lon"))
        # Hash the canonical record and its array position. This creates a
        # deterministic key within this payload while preserving duplicate
        # aircraft records as separate observations.
        canonical_record = json.dumps(
            aircraft,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
            ensure_ascii=True,
        )
        key_material = f"{index}:{canonical_record}".encode()
        source_record_key = hashlib.sha256(key_material).hexdigest()
        # Defensive collision handling; SHA-256 collisions are extremely
        # unlikely, but the database key must still be unique within a run.
        if source_record_key in seen_keys:
            raise ValueError("duplicate source_record_key generated")
        seen_keys.add(source_record_key)
        on_ground_value = aircraft.get("on_ground")
        on_ground = (
            on_ground_value if isinstance(on_ground_value, bool) else None
        )
        record: dict[str, Any] = {
            "run_id": run_id,
            "source_id": source_id,
            "source_type": source_type,
            "source_record_key": source_record_key,
            "observed_at": None,
            "aircraft_id": None,
            "icao24": icao24,
            "callsign": _optional_text(aircraft.get("flight")),
            "latitude_deg": latitude,
            "longitude_deg": longitude,
            "altitude_ft": _optional_float(aircraft.get("alt_baro")),
            "on_ground": on_ground,
            "assigned_airport_id": None,
            "assignment_distance_nm": None,
            "assignment_reason": None,
            "assignment_rule_version": None,
            "raw_payload": dict(aircraft) if include_raw_payload else None,
        }
        records.append(record)
    return records
