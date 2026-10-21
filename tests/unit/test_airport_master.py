import json
import pandas as pd
import pytest
from flight_intelligence.transforms.airport_master import build_master
def sample_rows():
    return [
        {
            "id": 1, "ident": "VAAA", "type": "large_airport",
            "name": "Example Airport", "latitude_deg": 19.0,
            "longitude_deg": 72.0, "elevation_ft": 39,
            "iso_country": "IN", "iso_region": "IN-MH",
            "municipality": "Mumbai", "scheduled_service": "yes",
            "icao_code": "VAAA", "iata_code": "AAA",
        },
        {
            "id": 2, "ident": "IN-H1", "type": "heliport",
            "name": "Example Heliport", "latitude_deg": 19.1,
            "longitude_deg": 72.1, "elevation_ft": 20,
            "iso_country": "IN", "iso_region": "IN-MH",
            "municipality": "Mumbai", "scheduled_service": "no",
            "icao_code": None, "iata_code": None,
        },
        {
            "id": 3, "ident": "VBBB", "type": "medium_airport",
            "name": "Outside India Example", "latitude_deg": 1.0,
            "longitude_deg": 2.0, "elevation_ft": 10,
            "iso_country": "US", "iso_region": "US-XX",
            "municipality": "Example", "scheduled_service": "no",
            "icao_code": None, "iata_code": None,
        },
    ]
def write_source(tmp_path, rows):
    source = tmp_path / "airports.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    return source
def test_includes_indian_airports_and_excludes_other_types(tmp_path):
    source = write_source(tmp_path, sample_rows())
    output = tmp_path / "master.csv"
    report_path = tmp_path / "report.json"
    report = build_master(source, output, report_path)
    master = pd.read_csv(output)
    assert len(master) == 1
    assert master.iloc[0]["name"] == "Example Airport"
    assert report["source_rows_india"] == 2
    assert report["candidate_count"] == 1
    assert report["accepted_master_count"] == 1
    assert report["excluded_india_records_by_type"]["heliport"] == 1
    assert json.loads(report_path.read_text(encoding="utf-8"))["accepted_master_count"] == 1
@pytest.mark.parametrize(
    ("field", "bad_value", "error_key"),
    [
        ("name", "", "missing_name"),
        ("latitude_deg", 95, "invalid_latitude"),
        ("longitude_deg", 200, "invalid_longitude"),
    ],
)
def test_rejects_invalid_candidate_fields(tmp_path, field, bad_value, error_key):
    rows = sample_rows()
    rows[0][field] = bad_value
    source = write_source(tmp_path, rows)
    report = build_master(
        source,
        tmp_path / "master.csv",
        tmp_path / "report.json",
    )
    assert report["accepted_master_count"] == 0
    assert report["rejected_candidate_count"] == 1
    assert report["validation_error_counts"][error_key] == 1
def test_missing_required_source_column_fails(tmp_path):
    rows = sample_rows()
    for row in rows:
        row.pop("latitude_deg")
    source = write_source(tmp_path, rows)
    with pytest.raises(ValueError, match="missing required columns"):
        build_master(source, tmp_path / "master.csv", tmp_path / "report.json")
def test_duplicate_candidate_ids_are_rejected(tmp_path):
    rows = sample_rows()
    duplicate = rows[0].copy()
    duplicate["name"] = "Duplicate Airport"
    rows.append(duplicate)
    source = write_source(tmp_path, rows)
    report = build_master(
        source,
        tmp_path / "master.csv",
        tmp_path / "report.json",
    )
    assert report["validation_error_counts"]["duplicate_id"] == 2
    assert report["accepted_master_count"] == 0
    assert report["rejected_candidate_count"] == 2
