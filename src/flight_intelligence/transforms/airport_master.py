"""Build a validated India airport reference master from OurAirports data."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
INCLUDED_TYPES = {"large_airport", "medium_airport", "small_airport"}
REQUIRED_COLUMNS = {
    "id", "ident", "type", "name", "latitude_deg", "longitude_deg",
    "elevation_ft", "iso_country", "iso_region", "municipality",
    "scheduled_service", "icao_code", "iata_code",
}
def build_master(
    source: str | Path,
    output: str | Path,
    report_path: str | Path,
) -> dict:
    """Validate source records and write an India airport master and JSON report."""
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
    candidates = india.loc[india["type"].isin(INCLUDED_TYPES)].copy()
    candidate_count = len(candidates)
    for column in ("latitude_deg", "longitude_deg", "elevation_ft"):
        candidates[column] = pd.to_numeric(candidates[column], errors="coerce")
    checks = {
        "missing_id": candidates["id"].isna(),
        "missing_name": (
            candidates["name"].isna()
            | candidates["name"].astype("string").str.strip().eq("").fillna(True)
        ),
        "invalid_latitude": ~candidates["latitude_deg"].between(-90, 90),
        "invalid_longitude": ~candidates["longitude_deg"].between(-180, 180),
        "duplicate_id": candidates["id"].duplicated(keep=False),
    }
    invalid = pd.Series(False, index=candidates.index)
    error_counts = {}
    for reason, mask in checks.items():
        mask = mask.fillna(True)
        error_counts[reason] = int(mask.sum())
        invalid |= mask
    accepted = candidates.loc[~invalid].copy()
    accepted["source"] = "OurAirports"
    accepted["source_snapshot_date_utc"] = datetime.now(timezone.utc).date().isoformat()
    accepted["master_scope"] = "india_civil_airports_v1"
    columns = [
        "id", "ident", "type", "name", "latitude_deg", "longitude_deg",
        "elevation_ft", "iso_country", "iso_region", "municipality",
        "scheduled_service", "icao_code", "iata_code", "source",
        "source_snapshot_date_utc", "master_scope",
    ]
    accepted = accepted[columns].sort_values(
        ["type", "name", "id"], kind="stable"
    )
    report = {
        "source_file": str(source),
        "source_rows_worldwide": int(len(df)),
        "source_rows_india": int(len(india)),
        "source_duplicate_ids_worldwide": int(df["id"].duplicated().sum()),
        "india_records_by_type": type_counts,
        "included_types": sorted(INCLUDED_TYPES),
        "excluded_india_records_by_type": {
            key: value for key, value in type_counts.items()
            if key not in INCLUDED_TYPES
        },
        "candidate_count": candidate_count,
        "validation_error_counts": error_counts,
        "rejected_candidate_count": int(invalid.sum()),
        "accepted_master_count": int(len(accepted)),
        "scheduled_service_yes_in_master": int(
            accepted["scheduled_service"].eq("yes").sum()
        ),
        "scheduled_service_no_in_master": int(
            accepted["scheduled_service"].eq("no").sum()
        ),
        "iata_code_present_in_master": int(accepted["iata_code"].notna().sum()),
        "icao_code_present_in_master": int(accepted["icao_code"].notna().sum()),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope_note": (
            "Validated OurAirports-derived reference subset; not a complete "
            "inventory of all physical or operational Indian airports. "
            "Traffic tiers and operational status are not inferred."
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
