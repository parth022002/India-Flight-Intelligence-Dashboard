"""Airport traffic-tier configuration and classification helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_tier_config(path: str | Path = "config/thresholds.json") -> dict[str, Any]:
    """Load and minimally validate the tier configuration."""
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("tiers"), list):
        raise ValueError("Tier configuration must contain a 'tiers' list.")
    return data


def classify_airport_tier(
    annual_movements: int | None,
    config: dict[str, Any] | None = None,
) -> str:
    """Classify by inclusive configured bounds; unresolved and unknown values become T0."""
    if annual_movements is None:
        return "T0"
    if isinstance(annual_movements, bool) or not isinstance(annual_movements, int):
        raise TypeError("annual_movements must be an integer or None")
    if annual_movements < 0:
        raise ValueError("annual_movements cannot be negative")

    tiers = (config or load_tier_config())["tiers"]
    for tier in tiers:
        if tier.get("tier") == "T0":
            continue
        minimum = tier.get("annual_movements_min_inclusive")
        maximum = tier.get("annual_movements_max_inclusive")
        if minimum is None or tier.get("status") == "unresolved_movement_boundary":
            continue
        if annual_movements >= minimum and (maximum is None or annual_movements <= maximum):
            return str(tier["tier"])
    return "T0"
