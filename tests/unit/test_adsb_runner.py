import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "collect_adsb.py"


def run_script(*args):
    with patch.object(
        sys,
        "argv",
        ["collect_adsb.py", "--endpoint", "/test/endpoint", *args],
    ):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
    return exc_info.value.code


def test_dry_run_does_not_connect_to_database_or_network(capsys):
    with (
        patch(
            "flight_intelligence.storage.connection.connect_database",
            side_effect=AssertionError("Database connection must not occur"),
        ),
        patch(
            "flight_intelligence.collectors.adsb_client.AdsbClient",
            side_effect=AssertionError("HTTP client must not be created"),
        ),
    ):
        result = run_script("--dry-run")

    output = capsys.readouterr().out

    assert result == 0
    assert "DRY RUN: no database connection or network request was made." in output
    assert "Collection would be blocked by the current configuration." in output


def test_disabled_collection_exits_before_database_connection(capsys):
    with patch(
        "flight_intelligence.storage.connection.connect_database",
        side_effect=AssertionError("Database connection must not occur"),
    ):
        result = run_script()

    output = capsys.readouterr().err

    assert result == 2
    assert "BLOCKED:" in output
    assert "must all be true" in output


def test_missing_database_environment_variable_name_is_rejected(capsys):
    result = run_script("--database-url-env", " ")

    output = capsys.readouterr().err

    assert result == 2
    assert "--database-url-env must not be empty." in output


def test_invalid_source_id_is_rejected(capsys):
    result = run_script("--source-id", "0", "--dry-run")

    output = capsys.readouterr().err

    assert result == 2
    assert "--source-id must be a positive integer." in output
