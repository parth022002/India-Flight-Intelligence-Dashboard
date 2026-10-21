"""Basic pure validation helpers for airport records."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REQUIRED_AIRPORT_FIELDS = ("airport_id", "name", "latitude", "longitude")


def validate_airport_record(record: Mapping[str, Any]) -> list[str]:
    """Return validation errors; empty means required fields passed basic checks."""
    errors: list[str] = []
    for field in REQUIRED_AIRPORT_FIELDS:
        if record.get(field) is None or record.get(field) == "":
            errors.append(f"missing_required_field:{field}")

    for field, low, high in (("latitude", -90, 90), ("longitude", -180, 180)):
        value = record.get(field)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors.append(f"{field}_not_numeric")
            continue
        if not low <= number <= high:
            errors.append(f"{field}_out_of_range")
    return errors
