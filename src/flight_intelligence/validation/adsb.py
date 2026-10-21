
"""Validation helpers for ADS-B API response payloads."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

REQUIRED_AIRCRAFT_FIELDS = ("hex", "lat", "lon")


def validate_adsb_payload(payload: Any) -> list[str]:
    """Return structural validation errors for an ADS-B API response."""
    if not isinstance(payload, Mapping):
        return ["payload_not_object"]

    aircraft = payload.get("aircraft")
    if not isinstance(aircraft, list):
        return ["aircraft_not_list"]

    errors: list[str] = []
    for index, record in enumerate(aircraft):
        prefix = f"aircraft[{index}]"

        if not isinstance(record, Mapping):
            errors.append(f"{prefix}_not_object")
            continue

        for field in REQUIRED_AIRCRAFT_FIELDS:
            if record.get(field) is None or record.get(field) == "":
                errors.append(f"{prefix}_missing:{field}")

        for field, low, high in (
            ("lat", -90.0, 90.0),
            ("lon", -180.0, 180.0),
        ):
            value = record.get(field)
            if value is None or value == "":
                continue

            try:
                number = float(value)
            except (TypeError, ValueError):
                errors.append(f"{prefix}_{field}_not_numeric")
                continue

            if not isfinite(number):
                errors.append(f"{prefix}_{field}_not_finite")
            elif not low <= number <= high:
                errors.append(f"{prefix}_{field}_out_of_range")

    return errors
