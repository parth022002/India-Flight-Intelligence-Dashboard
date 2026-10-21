"""Tests for airport master import validation."""

from __future__ import annotations

import pandas as pd
import pytest

from flight_intelligence.storage.airport_import import (
    validate_airport_master,
)

CSV_PATH = "data/processed/india_airport_master.csv"


def test_validate_airport_master_accepts_current_master() -> None:
    """Validate all records in the generated airport master."""
    records = validate_airport_master(CSV_PATH)
    assert len(records) == 320
    assert len({(row["source_name"], row["source_airport_id"]) for row in records}) == 320
    assert {row["iso_country"] for row in records} == {"IN"}


def test_validate_airport_master_preserves_optional_missing_values() -> None:
    """Keep missing optional airport attributes as None."""
    records = validate_airport_master(CSV_PATH)
    assert sum(row["elevation_ft"] is None for row in records) == 29
    assert sum(row["municipality"] is None for row in records) == 55


def test_validate_airport_master_rejects_duplicate_ids(
    tmp_path,
) -> None:
    """Reject duplicate source IDs before database writes."""
    frame = pd.read_csv(CSV_PATH)
    frame.loc[1, "id"] = frame.loc[0, "id"]
    duplicate_path = tmp_path / "duplicate_airports.csv"
    frame.to_csv(duplicate_path, index=False)
    with pytest.raises(ValueError, match="present and unique"):
        validate_airport_master(duplicate_path)


def test_validate_airport_master_rejects_non_indian_record(
    tmp_path,
) -> None:
    """Reject records outside the configured India scope."""
    frame = pd.read_csv(CSV_PATH)
    frame.loc[0, "iso_country"] = "NP"
    invalid_path = tmp_path / "non_indian_airport.csv"
    frame.to_csv(invalid_path, index=False)
    with pytest.raises(ValueError, match="outside the India scope"):
        validate_airport_master(invalid_path)


def test_validate_airport_master_rejects_missing_columns(
    tmp_path,
) -> None:
    """Reject CSV files missing required columns."""
    frame = pd.read_csv(CSV_PATH).drop(columns=["master_scope"])
    invalid_path = tmp_path / "missing_column.csv"
    frame.to_csv(invalid_path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        validate_airport_master(invalid_path)


def test_import_airport_master_dry_run_does_not_use_database() -> None:
    """Validate records in dry-run mode without opening a DB transaction."""
    from unittest.mock import Mock

    from flight_intelligence.storage.airport_import import (
        import_airport_master,
    )

    connection = Mock()
    result = import_airport_master(
        connection,
        CSV_PATH,
        dry_run=True,
    )
    assert result == {
        "dry_run": True,
        "records_validated": 320,
        "records_upserted": 0,
    }
    connection.transaction.assert_not_called()
    connection.cursor.assert_not_called()


def test_import_airport_master_propagates_database_failure() -> None:
    """Propagate database errors so callers know the import failed."""
    from unittest.mock import MagicMock

    from flight_intelligence.storage.airport_import import (
        import_airport_master,
    )

    connection = MagicMock()
    connection.transaction.side_effect = RuntimeError("simulated DB failure")
    with pytest.raises(RuntimeError, match="simulated DB failure"):
        import_airport_master(
            connection,
            CSV_PATH,
            dry_run=False,
        )
    connection.transaction.assert_called_once()
