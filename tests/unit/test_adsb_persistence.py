"""Unit tests for ADS-B persistence validation."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from flight_intelligence.storage.adsb_persistence import (
    _validate_record,
    persist_adsb_observations,
)


@pytest.fixture
def observation() -> dict:
    return {
        "run_id": 10,
        "source_id": 20,
        "source_type": "live_poll",
        "source_record_key": "record-001",
        "observed_at": datetime(2026, 10, 21, 10, 0, tzinfo=UTC),
        "aircraft_id": None,
        "icao24": "a1b2c3",
        "callsign": "AI123",
        "latitude_deg": 19.0896,
        "longitude_deg": 72.8656,
        "altitude_ft": 35000.0,
        "on_ground": False,
        "assigned_airport_id": None,
        "assignment_distance_nm": None,
        "assignment_reason": None,
        "assignment_rule_version": None,
        "raw_payload": {"hex": "a1b2c3"},
    }


def test_raw_payload_is_excluded_by_default(observation: dict) -> None:
    record = _validate_record(
        observation,
        run_id=10,
        source_id=20,
        source_type="live_poll",
        include_raw_payload=False,
    )
    assert record["raw_payload"] is None


def test_raw_payload_is_wrapped_as_jsonb_when_enabled(observation: dict) -> None:
    from psycopg.types.json import Jsonb

    record = _validate_record(
        observation,
        run_id=10,
        source_id=20,
        source_type="live_poll",
        include_raw_payload=True,
    )
    assert isinstance(record["raw_payload"], Jsonb)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude_deg", 91),
        ("longitude_deg", -181),
        ("altitude_ft", float("nan")),
        ("assignment_distance_nm", -1),
        ("on_ground", "false"),
        ("source_record_key", " "),
    ],
)
def test_invalid_observation_fields_are_rejected(
    observation: dict, field: str, value: object
) -> None:
    observation[field] = value
    with pytest.raises(ValueError):
        _validate_record(
            observation,
            run_id=10,
            source_id=20,
            source_type="live_poll",
            include_raw_payload=False,
        )


def test_observation_run_id_must_match(observation: dict) -> None:
    observation["run_id"] = 11
    with pytest.raises(ValueError, match="run_id/source_id"):
        _validate_record(
            observation,
            run_id=10,
            source_id=20,
            source_type="live_poll",
            include_raw_payload=False,
        )


def test_observation_source_type_must_match(observation: dict) -> None:
    observation["source_type"] = "archive_sample"
    with pytest.raises(ValueError, match="source_type"):
        _validate_record(
            observation,
            run_id=10,
            source_id=20,
            source_type="live_poll",
            include_raw_payload=False,
        )


def test_invalid_record_is_rejected_before_database_access(observation: dict) -> None:
    connection = MagicMock()
    observation["latitude_deg"] = 91
    with pytest.raises(ValueError, match="latitude_deg"):
        persist_adsb_observations(
            connection,
            [observation],
            run_id=10,
            source_id=20,
        )
    connection.transaction.assert_not_called()


def test_duplicate_keys_in_batch_are_rejected(observation: dict) -> None:
    duplicate = dict(observation)
    connection = MagicMock()
    with pytest.raises(ValueError, match="unique"):
        persist_adsb_observations(
            connection,
            [observation, duplicate],
            run_id=10,
            source_id=20,
        )
    connection.transaction.assert_not_called()


@pytest.mark.parametrize("run_id,source_id", [(0, 20), (10, 0), (True, 20)])
def test_invalid_ids_are_rejected_before_database_access(
    observation: dict, run_id: int, source_id: int
) -> None:
    connection = MagicMock()
    with pytest.raises(ValueError):
        persist_adsb_observations(
            connection,
            [observation],
            run_id=run_id,
            source_id=source_id,
        )
    connection.transaction.assert_not_called()


def test_received_count_must_match_accepted_plus_rejected(
    observation: dict,
) -> None:
    connection = MagicMock()
    with pytest.raises(ValueError, match="accepted plus rejected"):
        persist_adsb_observations(
            connection,
            [observation],
            run_id=10,
            source_id=20,
            records_received=5,
            records_rejected=0,
        )
    connection.transaction.assert_not_called()


def test_persist_observations_inserts_and_finalizes_successfully(
    observation: dict,
) -> None:
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ("live_poll", "running", 20)
    cursor.rowcount = 1
    result = persist_adsb_observations(
        connection,
        [observation],
        run_id=10,
        source_id=20,
    )
    assert result == {
        "run_id": 10,
        "status": "succeeded",
        "records_received": 1,
        "records_accepted": 1,
        "records_rejected": 0,
    }
    connection.transaction.assert_called_once()
    cursor.executemany.assert_called_once()
    cursor.execute.assert_called()
    assert "UPDATE collection_runs" in cursor.execute.call_args[0][0]


def test_persist_observations_finalizes_partial_run_when_records_rejected(
    observation: dict,
) -> None:
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ("live_poll", "running", 20)
    cursor.rowcount = 1
    result = persist_adsb_observations(
        connection,
        [observation],
        run_id=10,
        source_id=20,
        records_received=3,
        records_rejected=2,
    )
    assert result == {
        "run_id": 10,
        "status": "partial",
        "records_received": 3,
        "records_accepted": 1,
        "records_rejected": 2,
    }
    finalization_call = cursor.execute.call_args_list[-1]
    assert "UPDATE collection_runs" in finalization_call.args[0]
    assert finalization_call.args[1]["status"] == "partial"
    assert finalization_call.args[1]["error_code"] == "records_rejected"
    assert finalization_call.args[1]["records_received"] == 3
    assert finalization_call.args[1]["records_accepted"] == 1
    assert finalization_call.args[1]["records_rejected"] == 2


def test_insert_failure_propagates_without_finalizing_run(
    observation: dict,
) -> None:
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ("live_poll", "running", 20)
    cursor.executemany.side_effect = RuntimeError("simulated insert failure")
    with pytest.raises(RuntimeError, match="simulated insert failure"):
        persist_adsb_observations(
            connection,
            [observation],
            run_id=10,
            source_id=20,
        )
    connection.transaction.assert_called_once()
    cursor.executemany.assert_called_once()
    assert not any(
        "UPDATE collection_runs" in str(call.args[0]) for call in cursor.execute.call_args_list
    )
