"""Safely run one ADS-B collection attempt.

Collection is disabled by default. The script never registers or approves
data sources and requires an explicitly selected database URL environment
variable. Dry-run mode performs no database connection or network request.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from flight_intelligence.collectors.adsb_client import AdsbClient
from flight_intelligence.collectors.adsb_orchestrator import run_adsb_collection
from flight_intelligence.config import build_adsb_client_config, get_log_level, load_json_config
from flight_intelligence.storage.connection import connect_database

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "settings.example.json"
DEFAULT_DATABASE_ENV_VAR = "FLIGHT_INTEL_DATABASE_URL"
DEFAULT_ENDPOINT = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a guarded ADS-B collection attempt.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Configuration JSON path (default: config/settings.example.json).",
    )
    parser.add_argument(
        "--database-url-env",
        default=DEFAULT_DATABASE_ENV_VAR,
        help=(
            "Environment variable containing the database URL. "
            "No fallback to DATABASE_URL is performed."
        ),
    )
    parser.add_argument(
        "--source-id",
        type=int,
        help="Existing data_sources.source_id for an approved adsb.lol source.",
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        help="Provider-approved relative ADS-B API endpoint path.",
    )
    parser.add_argument(
        "--include-raw-payload",
        action="store_true",
        help="Persist raw payload only when explicitly requested.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and print the plan; make no DB or network requests.",
    )
    return parser.parse_args()


def _safe_configuration_summary(config: dict[str, Any]) -> dict[str, Any]:
    """Return non-secret, non-payload configuration facts."""
    collection = config.get("collection", {})
    adsb = config.get("adsb", {})
    return {
        "collection_enabled": collection.get("enabled", False),
        "adsb_enabled": adsb.get("enabled", False),
        "pilot_mode": adsb.get("pilot_mode", False),
        "provider": adsb.get("provider", "adsb.lol"),
        "base_url": adsb.get("base_url", "https://api.adsb.lol"),
    }


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=get_log_level(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.database_url_env.strip():
        print("ERROR: --database-url-env must not be empty.", file=sys.stderr)
        return 2

    if args.source_id is not None and args.source_id < 1:
        print("ERROR: --source-id must be a positive integer.", file=sys.stderr)
        return 2

    try:
        config = load_json_config(args.config)
        client_config = build_adsb_client_config(config)
    except (OSError, ValueError, TypeError) as exc:
        print(
            f"ERROR: configuration could not be loaded or validated ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 2

    summary = _safe_configuration_summary(config)
    print("ADS-B collection runner")
    print(f"Configuration: {args.config}")
    print(f"Database URL environment variable: {args.database_url_env}")
    print(f"Provider: {summary['provider']}")
    print(f"Collection enabled: {summary['collection_enabled']}")
    print(f"ADS-B enabled: {summary['adsb_enabled']}")
    print(f"Pilot mode: {summary['pilot_mode']}")
    print(f"Dry run: {args.dry_run}")
    print("Raw payload persistence: " + str(args.include_raw_payload))

    # Dry-run never connects to PostgreSQL and never instantiates an HTTP client.
    if args.dry_run:
        print("DRY RUN: no database connection or network request was made.")
        if not client_config.enabled:
            print("Collection would be blocked by the current configuration.")
        elif args.source_id is None:
            print("Collection would require --source-id for an existing approved source.")
        else:
            print(
                "Configuration gates passed; source approval must still be checked in the database."
            )
        return 0

    # Do not attempt a DB connection or network call while collection is disabled.
    if not client_config.enabled:
        print(
            "BLOCKED: collection, ADS-B, and pilot-mode switches must all be true.",
            file=sys.stderr,
        )
        return 2

    if args.source_id is None:
        print(
            "BLOCKED: --source-id is required; sources are never "
            "registered or approved automatically.",
            file=sys.stderr,
        )
        return 2

    try:
        connection = connect_database(url_env_var=args.database_url_env)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        with connection:
            with AdsbClient(client_config) as client:
                result = run_adsb_collection(
                    connection,
                    client,
                    source_id=args.source_id,
                    endpoint=args.endpoint,
                    include_raw_payload=args.include_raw_payload,
                )
        print(
            "Collection completed: "
            f"run_id={result['run_id']} "
            f"status={result['status']} "
            f"accepted={result['records_accepted']}"
        )
        return 0
    except (ValueError, RuntimeError) as exc:
        print(
            f"ERROR: collection did not complete ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        # Do not print exception text: it may contain provider or connection details.
        logging.getLogger(__name__).error(
            "Collection failed with exception type %s",
            type(exc).__name__,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
