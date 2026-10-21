"""Unit tests for ADS-B payload normalization."""
from __future__ import annotations

from copy import deepcopy

import pytest

from flight_intelligence.collectors.adsb_normalizer import normalize_adsb_payload


@pytest.fixture
def payload() -> dict:
    return {
        "aircraft": [
            {
                "hex": "A1B2C3",
                "lat": 19.0896,
                "lon": 72.8656,
                "flight": " AI123 ",
                "alt_baro": 35000,
                "on_ground": False,
            },
            {
                "hex": "d4e5f6",
                "lat": 28.5562,
                "lon": 77.1,
            },
        ]
    }
def test_normalizes_fields_and_keeps_assignment_unset(payload: dict) -> None:
    records = normalize_adsb_payload(payload, run_id=1, source_id=2)
    assert len(records) == 2
    first = records[0]
    assert first["run_id"] == 1
    assert first["source_id"] == 2
    assert first["source_type"] == "live_poll"
    assert first["icao24"] == "a1b2c3"
    assert first["aircraft_id"] is None
    assert first["callsign"] == "AI123"
    assert first["latitude_deg"] == pytest.approx(19.0896)
    assert first["longitude_deg"] == pytest.approx(72.8656)
    assert first["altitude_ft"] == pytest.approx(35000)
    assert first["on_ground"] is False
    assert first["observed_at"] is None
    assert first["assigned_airport_id"] is None
    assert first["assignment_distance_nm"] is None
    assert first["assignment_reason"] is None
    assert first["assignment_rule_version"] is None
def test_missing_optional_fields_remain_none(payload: dict) -> None:
    records = normalize_adsb_payload(payload, run_id=1, source_id=2)
    second = records[1]
    assert second["callsign"] is None
    assert second["altitude_ft"] is None
    assert second["on_ground"] is None
    assert second["observed_at"] is None
    assert second["raw_payload"] is None
def test_raw_payload_is_off_by_default_and_opt_in(payload: dict) -> None:
    without_raw = normalize_adsb_payload(payload, run_id=1, source_id=2)
    with_raw = normalize_adsb_payload(
        payload, run_id=1, source_id=2, include_raw_payload=True
    )
    assert without_raw[0]["raw_payload"] is None
    assert with_raw[0]["raw_payload"] == payload["aircraft"][0]
    assert with_raw[0]["raw_payload"] is not payload["aircraft"][0]
def test_record_keys_are_deterministic_for_same_payload(payload: dict) -> None:
    first = normalize_adsb_payload(payload, run_id=1, source_id=2)
    second = normalize_adsb_payload(deepcopy(payload), run_id=1, source_id=2)
    assert [r["source_record_key"] for r in first] == [
        r["source_record_key"] for r in second
    ]
def test_duplicate_aircraft_entries_get_distinct_keys(payload: dict) -> None:
    payload["aircraft"].append(deepcopy(payload["aircraft"][0]))
    records = normalize_adsb_payload(payload, run_id=1, source_id=2)
    keys = [record["source_record_key"] for record in records]
    assert len(keys) == len(set(keys))
def test_invalid_payload_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid ADS-B payload"):
        normalize_adsb_payload({"aircraft": "invalid"}, run_id=1, source_id=2)
@pytest.mark.parametrize(
    ("run_id", "source_id"),
    [(0, 1), (1, 0), (-1, 1), (True, 1), (1, False)],
)
def test_invalid_database_ids_are_rejected(run_id: int, source_id: int) -> None:
    with pytest.raises(ValueError):
        normalize_adsb_payload(
            {"aircraft": []}, run_id=run_id, source_id=source_id
        )
def test_invalid_source_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="source_type"):
        normalize_adsb_payload(
            {"aircraft": []}, run_id=1, source_id=2, source_type="unknown"
        )
def test_archive_sample_source_type_is_supported(payload: dict) -> None:
    records = normalize_adsb_payload(
        payload, run_id=3, source_id=4, source_type="archive_sample"
    )
    assert all(record["source_type"] == "archive_sample" for record in records)
