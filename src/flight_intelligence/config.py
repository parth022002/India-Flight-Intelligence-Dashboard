"""Configuration loading helpers with safe defaults."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from flight_intelligence.collectors.adsb_client import AdsbClientConfig

DEFAULT_CONFIG_PATH = Path("config/settings.example.json")


def load_json_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load a JSON configuration file and require a top-level object."""
    with Path(path).open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    if not isinstance(config, dict):
        raise ValueError("configuration must be a JSON object")

    return config


def get_log_level(default: str = "INFO") -> str:
    """Return the configured logging level."""
    return os.getenv("LOG_LEVEL", default).upper()


def build_adsb_client_config(config: dict[str, Any]) -> AdsbClientConfig:
    """Build a validated ADS-B client configuration with safe defaults."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be an object")

    collection = config.get("collection", {})
    adsb = config.get("adsb", {})
    limits = config.get("limits", {})

    if not isinstance(collection, dict):
        raise ValueError("collection configuration must be an object")
    if not isinstance(adsb, dict):
        raise ValueError("adsb configuration must be an object")
    if not isinstance(limits, dict):
        raise ValueError("limits configuration must be an object")

    collection_enabled = collection.get("enabled", False)
    adsb_enabled = adsb.get("enabled", False)
    pilot_mode = adsb.get("pilot_mode", False)

    if not isinstance(pilot_mode, bool):
        raise ValueError("adsb.pilot_mode must be a boolean")

    if not isinstance(collection_enabled, bool):
        raise ValueError("collection.enabled must be a boolean")
    if not isinstance(adsb_enabled, bool):
        raise ValueError("adsb.enabled must be a boolean")

    max_requests = adsb.get("max_requests_per_run", 2)
    overall_max_requests = limits.get("max_requests_per_run", 10)
    max_payload_mb = adsb.get("max_payload_mb_per_run", 5)
    overall_max_payload_mb = limits.get("max_payload_mb_per_run", 25)

    for name, value in (
        ("adsb.max_requests_per_run", max_requests),
        ("limits.max_requests_per_run", overall_max_requests),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")

    for name, value in (
        ("adsb.max_payload_mb_per_run", max_payload_mb),
        ("limits.max_payload_mb_per_run", overall_max_payload_mb),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{name} must be a finite number")

    if overall_max_requests < 1:
        raise ValueError("limits.max_requests_per_run must be at least 1")
    if max_requests < 1 or max_requests > overall_max_requests:
        raise ValueError("ADS-B request budget exceeds application limits")

    if overall_max_payload_mb <= 0:
        raise ValueError("limits.max_payload_mb_per_run must be positive")
    if max_payload_mb <= 0 or max_payload_mb > overall_max_payload_mb:
        raise ValueError("ADS-B payload budget exceeds application limits")

    timeout_seconds = adsb.get("request_timeout_seconds", 20)
    max_retries = adsb.get("max_retries", 2)
    retry_backoff_seconds = adsb.get("retry_backoff_seconds", 2)

    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("adsb.request_timeout_seconds must be positive")

    if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError("adsb.max_retries must be a nonnegative integer")

    if (
        isinstance(retry_backoff_seconds, bool)
        or not isinstance(retry_backoff_seconds, (int, float))
        or not math.isfinite(retry_backoff_seconds)
        or retry_backoff_seconds < 0
    ):
        raise ValueError("adsb.retry_backoff_seconds must be nonnegative")

    return AdsbClientConfig(
        base_url=adsb.get("base_url", "https://api.adsb.lol"),
        timeout_seconds=float(timeout_seconds),
        max_retries=max_retries,
        retry_backoff_seconds=float(retry_backoff_seconds),
        max_requests_per_run=max_requests,
        max_payload_bytes_per_run=int(max_payload_mb * 1024 * 1024),
        enabled=adsb_enabled and collection_enabled and pilot_mode,
    )
