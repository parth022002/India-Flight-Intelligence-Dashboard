import json

import pytest

from flight_intelligence.analytics.tiers import classify_airport_tier
from flight_intelligence.config import (
    build_adsb_client_config,
    load_json_config,
)


def test_example_settings_load_as_object():
    config = load_json_config("config/settings.example.json")
    assert config["app"]["name"] == "India Flight Intelligence"
    assert config["collection"]["enabled"] is False


def test_invalid_top_level_config_raises(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_json_config(path)


@pytest.mark.parametrize(
    ("movements", "expected"),
    [(None, "T0"), (0, "T0"), (999, "T0"), (1000, "T4"),
     (11999, "T4"), (12000, "T3"), (40000, "T2"), (100000, "T1")],
)
def test_tier_classification(movements, expected):
    assert classify_airport_tier(movements) == expected


def test_negative_movements_rejected():
    with pytest.raises(ValueError):
        classify_airport_tier(-1)


def test_adsb_client_config_uses_safe_example_settings():
    config = load_json_config("config/settings.example.json")
    client_config = build_adsb_client_config(config)

    assert client_config.enabled is False
    assert client_config.max_requests_per_run == 2
    assert client_config.max_payload_bytes_per_run == 5 * 1024 * 1024
    assert client_config.timeout_seconds == 20


def test_adsb_cannot_enable_when_global_collection_is_disabled():
    config = {
        "collection": {"enabled": False},
        "adsb": {
            "enabled": True,
            "max_requests_per_run": 2,
            "max_payload_mb_per_run": 5,
        },
        "limits": {
            "max_requests_per_run": 10,
            "max_payload_mb_per_run": 25,
        },
    }

    client_config = build_adsb_client_config(config)
    assert client_config.enabled is False


def test_adsb_config_remains_disabled_when_adsb_switch_is_missing():
    config = {
        "collection": {"enabled": True},
        "limits": {
            "max_requests_per_run": 10,
            "max_payload_mb_per_run": 25,
        },
    }

    client_config = build_adsb_client_config(config)
    assert client_config.enabled is False


def test_adsb_request_budget_cannot_exceed_global_limit():
    config = {
        "collection": {"enabled": False},
        "adsb": {
            "enabled": False,
            "max_requests_per_run": 11,
            "max_payload_mb_per_run": 5,
        },
        "limits": {
            "max_requests_per_run": 10,
            "max_payload_mb_per_run": 25,
        },
    }

    with pytest.raises(ValueError, match="request budget"):
        build_adsb_client_config(config)


def test_adsb_payload_budget_cannot_exceed_global_limit():
    config = {
        "collection": {"enabled": False},
        "adsb": {
            "enabled": False,
            "max_requests_per_run": 2,
            "max_payload_mb_per_run": 30,
        },
        "limits": {
            "max_requests_per_run": 10,
            "max_payload_mb_per_run": 25,
        },
    }

    with pytest.raises(ValueError, match="payload budget"):
        build_adsb_client_config(config)


@pytest.mark.parametrize(
    "collection",
    [None, [], "enabled", 123],
)
def test_invalid_collection_section_is_rejected(collection):
    config = {
        "collection": collection,
        "adsb": {"enabled": False},
        "limits": {
            "max_requests_per_run": 10,
            "max_payload_mb_per_run": 25,
        },
    }

    with pytest.raises(ValueError, match="collection"):
        build_adsb_client_config(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("request_timeout_seconds", 0),
        ("request_timeout_seconds", -1),
        ("max_retries", -1),
        ("max_retries", 1.5),
        ("retry_backoff_seconds", -1),
    ],
)
def test_invalid_adsb_timeout_and_retry_settings_are_rejected(field, value):
    config = {
        "collection": {"enabled": False},
        "adsb": {
            "enabled": False,
            "max_requests_per_run": 2,
            "max_payload_mb_per_run": 5,
            field: value,
        },
        "limits": {
            "max_requests_per_run": 10,
            "max_payload_mb_per_run": 25,
        },
    }

    with pytest.raises(ValueError):
        build_adsb_client_config(config)


def test_adsb_switch_must_be_a_boolean():
    config = {
        "collection": {"enabled": True},
        "adsb": {
            "enabled": "true",
            "max_requests_per_run": 2,
            "max_payload_mb_per_run": 5,
        },
        "limits": {
            "max_requests_per_run": 10,
            "max_payload_mb_per_run": 25,
        },
    }

    with pytest.raises(ValueError, match="enabled"):
        build_adsb_client_config(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_payload_mb_per_run", float("nan")),
        ("max_payload_mb_per_run", float("inf")),
        ("request_timeout_seconds", float("nan")),
        ("request_timeout_seconds", float("inf")),
        ("retry_backoff_seconds", float("nan")),
        ("retry_backoff_seconds", float("inf")),
    ],
)
def test_non_finite_adsb_numeric_settings_are_rejected(field, value):
    config = {
        "collection": {"enabled": False},
        "adsb": {
            "enabled": False,
            "max_requests_per_run": 2,
            "max_payload_mb_per_run": 5,
            "request_timeout_seconds": 20,
            "retry_backoff_seconds": 2,
            field: value,
        },
        "limits": {
            "max_requests_per_run": 10,
            "max_payload_mb_per_run": 25,
        },
    }
    with pytest.raises(ValueError):
        build_adsb_client_config(config)
