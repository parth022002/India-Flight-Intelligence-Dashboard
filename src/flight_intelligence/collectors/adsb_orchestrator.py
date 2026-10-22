"""Orchestrate a single ADS-B collection run safely."""
from __future__ import annotations

import logging
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from flight_intelligence.collectors.adsb_client import (
    AdsbClient,
    AdsbClientError,
)
from flight_intelligence.collectors.adsb_normalizer import normalize_adsb_payload
from flight_intelligence.storage.adsb_persistence import persist_adsb_observations

logger = logging.getLogger(__name__)
SOURCE_LOOKUP_SQL = """
SELECT source_name, data_type, license_status
FROM data_sources
WHERE source_id = %s
"""
CREATE_RUN_SQL = """
INSERT INTO collection_runs (source_id, run_type, status, metadata)
VALUES (%s, 'live_poll', 'running', %s)
RETURNING run_id
"""
FAIL_RUN_SQL = """
UPDATE collection_runs
SET status = 'failed',
    finished_at = NOW(),
    error_code = %s,
    error_summary = %s
WHERE run_id = %s
  AND status = 'running'
"""
def _create_run(
    connection: psycopg.Connection,
    source_id: int,
) -> int:
    """Create and commit a run before any network request."""
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                CREATE_RUN_SQL,
                (source_id, Jsonb({"collector": "adsb_orchestrator"})),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Database did not return a collection run ID")
            return int(row[0])
def _mark_run_failed(
    connection: psycopg.Connection,
    *,
    run_id: int,
    error_code: str,
) -> None:
    """Record a sanitized failure without exposing provider response details."""
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                FAIL_RUN_SQL,
                (
                    error_code,
                    "ADS-B collection failed; inspect sanitized application logs.",
                    run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Failed collection run could not be finalized")
def run_adsb_collection(
    connection: psycopg.Connection,
    client: AdsbClient,
    *,
    source_id: int,
    endpoint: str,
    include_raw_payload: bool = False,
) -> dict[str, int | str]:
    """Collect one ADS-B payload, normalize it, and persist it atomically.
    The source must already be registered and explicitly approved. This
    function never registers a source and never enables a disabled client.
    """
    if isinstance(source_id, bool) or not isinstance(source_id, int) or source_id < 1:
        raise ValueError("source_id must be a positive integer")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("endpoint must be a non-empty string")
    if not isinstance(include_raw_payload, bool):
        raise ValueError("include_raw_payload must be a boolean")
    if not client.config.enabled:
        raise AdsbClientError("ADS-B collection is disabled by configuration")
    # Source validation completes before creating a run or making a request.
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(SOURCE_LOOKUP_SQL, (source_id,))
            source = cursor.fetchone()
    if source is None:
        raise ValueError("Registered ADS-B source does not exist")
    source_name, data_type, license_status = source
    if data_type != "adsb_api":
        raise ValueError("Registered source is not an ADS-B API source")
    if license_status != "approved":
        raise ValueError("ADS-B source terms must be approved before collection")
    if source_name != "adsb.lol":
        raise ValueError("Registered source does not match the configured ADS-B provider")
    run_id = _create_run(connection, source_id)
    try:
        payload: dict[str, Any] = client.fetch_aircraft(endpoint)
        observations = normalize_adsb_payload(
            payload,
            run_id=run_id,
            source_id=source_id,
            source_type="live_poll",
            include_raw_payload=include_raw_payload,
        )
        result = persist_adsb_observations(
            connection,
            observations,
            run_id=run_id,
            source_id=source_id,
            source_type="live_poll",
            records_received=len(observations),
            records_rejected=0,
            include_raw_payload=include_raw_payload,
        )
        logger.info(
            "ADS-B collection completed: run_id=%d status=%s accepted=%d",
            run_id,
            result["status"],
            result["records_accepted"],
        )
        return result
    except Exception as exc:
        # Do not log exception text: HTTP errors may include sensitive details.
        error_code = (
            "adsb_request_failed"
            if isinstance(exc, AdsbClientError)
            else "adsb_processing_failed"
        )
        logger.warning(
            "ADS-B collection failed: run_id=%d error_type=%s",
            run_id,
            type(exc).__name__,
        )
        try:
            _mark_run_failed(
                connection,
                run_id=run_id,
                error_code=error_code,
            )
        except Exception as finalize_exc:
            logger.error(
                "Could not finalize failed ADS-B run: run_id=%d error_type=%s",
                run_id,
                type(finalize_exc).__name__,
            )
        raise
