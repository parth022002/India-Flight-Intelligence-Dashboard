
"""Build a validated India aviation-facilities inventory from OurAirports data."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "id",
    "ident",
    "type",
    "name",
    "latitude_deg",
    "longitude_deg",
    "iso_country",
    "iso_region",
    "municipality",
    "scheduled_service",
    "icao_code",
    "iata_code",
}


def build_facilities(
    source: str | Path,
    output: str | Path,
    report_path: str | Path,
) -> dict:
    """Validate and write an India-wide source-classified facilities inventory."""
    source = Path(source)
    output = Path(output)
    report_path = Path(report_path)

    if not source.is_file():
        raise FileNotFoundError(f"Source CSV not found: {source}")

    df = pd.read_csv(source, low_memory=False)
    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Source is missing required columns: {missing_columns}")

    india = df.loc[df["iso_country"].eq("IN")].copy()
    type_counts = {
        str(key): int(value)
        for key, value in india["type"].value_counts(dropna=False).items()
    }

    candidates = india.copy()
    candidates["latitude_deg"] = pd.to_numeric(
        candidates["latitude_deg"], errors="coerce"
    )
    candidates["longitude_deg"] = pd.to_numeric(
        candidates["longitude_deg"], errors="coerce"
    )

    checks = {
        "missing_id": (
            candidates["id"].isna()
            | candidates["id"].astype("string").str.strip().eq("").fillna(True)
        ),
        "missing_ident": (
            candidates["ident"].isna()
            | candidates["ident"].astype("string").str.strip().eq("").fillna(True)
        ),
        "missing_type": (
            candidates["type"].isna()
            | candidates["type"].astype("string").str.strip().eq("").fillna(True)
        ),
        "missing_name": (
            candidates["name"].isna()
            | candidates["name"].astype("string").str.strip().eq("").fillna(True)
        ),
        "invalid_latitude": ~candidates["latitude_deg"].between(-90, 90),
        "invalid_longitude": ~candidates["longitude_deg"].between(-180, 180),
        "duplicate_id": candidates["id"].duplicated(keep=False),
    }

    invalid = pd.Series(False, index=candidates.index)
    error_counts: dict[str, int] = {}
    for reason, mask in checks.items():
        mask = mask.fillna(True)
        error_counts[reason] = int(mask.sum())
        invalid |= mask

    accepted = candidates.loc[~invalid].copy()
    accepted["source"] = "OurAirports"
    accepted["build_date_utc"] = datetime.now(UTC).date().isoformat()
    accepted["master_scope"] = "india_aviation_facilities_v1"

    columns = [
        "id",
        "ident",
        "type",
        "name",
        "latitude_deg",
        "longitude_deg",
        "iso_country",
        "iso_region",
        "municipality",
        "scheduled_service",
        "icao_code",
        "iata_code",
        "source",
        "build_date_utc",
        "master_scope",
    ]
    accepted = accepted[columns].sort_values(
        ["type", "name", "id"], kind="stable"
    )

    report = {
        "source_file": str(source),
        "source_rows_worldwide": int(len(df)),
        "source_rows_india": int(len(india)),
        "source_duplicate_ids_worldwide": int(df["id"].duplicated().sum()),
        "source_records_by_type": type_counts,
        "candidate_count": int(len(candidates)),
        "validation_error_counts": error_counts,
        "rejected_candidate_count": int(invalid.sum()),
        "accepted_facility_count": int(len(accepted)),
        "accepted_records_by_type": {
            str(key): int(value)
            for key, value in accepted["type"].value_counts(dropna=False).items()
        },
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope_note": (
            "OurAirports-derived reference inventory of source-classified Indian "
            "aviation facilities. Source type is not independently verified "
            "operational status. This inventory does not establish national "
            "completeness or authorization to redistribute source data."
        ),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_tmp = output.with_suffix(output.suffix + ".tmp")
    report_tmp = report_path.with_suffix(report_path.suffix + ".tmp")

    accepted.to_csv(output_tmp, index=False)
    report_tmp.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    output_tmp.replace(output)
    report_tmp.replace(report_path)

    return report
