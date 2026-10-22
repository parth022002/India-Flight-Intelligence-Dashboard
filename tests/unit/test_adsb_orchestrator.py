from unittest.mock import MagicMock

import pytest

from flight_intelligence.collectors.adsb_client import AdsbClientError
from flight_intelligence.collectors.adsb_orchestrator import run_adsb_collection


def make_connection(source=("adsb.lol", "adsb_api", "approved"), run_id=42):
    connection = MagicMock()
    cursor = MagicMock()
    connection.transaction.return_value.__enter__.return_value = None
    connection.transaction.return_value.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False
    cursor.fetchone.side_effect = [source, (run_id,)]
    cursor.rowcount = 1
    return connection, cursor
def make_client(*, enabled=True, payload=None, error=None):
    client = MagicMock()
    client.config.enabled = enabled
    if error is not None:
        client.fetch_aircraft.side_effect = error
    else:
        client.fetch_aircraft.return_value = payload or {"aircraft": []}
    return client
def test_disabled_client_does_not_query_database():
    connection = MagicMock()
    client = make_client(enabled=False)
    with pytest.raises(AdsbClientError, match="disabled"):
        run_adsb_collection(
            connection,
            client,
            source_id=1,
            endpoint="/v0/test",
        )
    connection.cursor.assert_not_called()
    client.fetch_aircraft.assert_not_called()
def test_unapproved_source_is_rejected_before_run_creation():
    connection, cursor = make_connection(
        source=("adsb.lol", "adsb_api", "not_reviewed")
    )
    client = make_client()
    with pytest.raises(ValueError, match="must be approved"):
        run_adsb_collection(
            connection,
            client,
            source_id=1,
            endpoint="/v0/test",
        )
    assert cursor.execute.call_count == 1
    client.fetch_aircraft.assert_not_called()
def test_successful_collection_persists_normalized_observations(monkeypatch):
    connection, cursor = make_connection()
    client = make_client(payload={"aircraft": []})
    persisted = {
        "run_id": 42,
        "status": "succeeded",
        "records_received": 0,
        "records_accepted": 0,
        "records_rejected": 0,
    }
    normalized = []
    def fake_normalize(payload, **kwargs):
        normalized.append((payload, kwargs))
        return []
    def fake_persist(conn, observations, **kwargs):
        assert conn is connection
        assert observations == []
        assert kwargs["run_id"] == 42
        assert kwargs["source_id"] == 1
        return persisted
    monkeypatch.setattr(
        "flight_intelligence.collectors.adsb_orchestrator.normalize_adsb_payload",
        fake_normalize,
    )
    monkeypatch.setattr(
        "flight_intelligence.collectors.adsb_orchestrator.persist_adsb_observations",
        fake_persist,
    )
    result = run_adsb_collection(
        connection,
        client,
        source_id=1,
        endpoint="/v0/test",
    )
    assert result == persisted
    assert normalized[0][1]["run_id"] == 42
    client.fetch_aircraft.assert_called_once_with("/v0/test")
    assert cursor.execute.call_count == 2
def test_request_failure_marks_run_failed(monkeypatch):
    connection, cursor = make_connection()
    client = make_client(error=AdsbClientError("synthetic request failure"))
    marked_failed = []
    def fake_mark_failed(conn, *, run_id, error_code):
        marked_failed.append((conn, run_id, error_code))
    monkeypatch.setattr(
        "flight_intelligence.collectors.adsb_orchestrator._mark_run_failed",
        fake_mark_failed,
    )
    with pytest.raises(AdsbClientError, match="synthetic request failure"):
        run_adsb_collection(
            connection,
            client,
            source_id=1,
            endpoint="/v0/test",
        )
    assert marked_failed == [(connection, 42, "adsb_request_failed")]
    assert cursor.execute.call_count == 2
def test_finalization_failure_does_not_mask_original_request_error(monkeypatch):
    connection, cursor = make_connection()
    original_error = AdsbClientError("synthetic request failure")
    client = make_client(error=original_error)

    def fail_to_mark_run_failed(conn, *, run_id, error_code):
        raise RuntimeError("synthetic database finalization failure")

    monkeypatch.setattr(
        "flight_intelligence.collectors.adsb_orchestrator._mark_run_failed",
        fail_to_mark_run_failed,
    )

    with pytest.raises(AdsbClientError, match="synthetic request failure") as exc_info:
        run_adsb_collection(
            connection,
            client,
            source_id=1,
            endpoint="/v0/test",
        )

    assert exc_info.value is original_error
    assert cursor.execute.call_count == 2
