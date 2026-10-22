"""Apply reviewed PostgreSQL migrations."""
from __future__ import annotations

import argparse
from pathlib import Path

from flight_intelligence.storage.connection import connect_database
from flight_intelligence.storage.migrations import apply_migrations

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = PROJECT_ROOT / "sql" / "migrations"
MIGRATION_DATABASE_URL_ENV = "FLIGHT_INTEL_MIGRATION_DATABASE_URL"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply pending database migrations."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate migration files without connecting to the database.",
    )
    args = parser.parse_args()

    if args.check:
        from flight_intelligence.storage.migrations import discover_migrations

        migrations = discover_migrations(MIGRATIONS_DIR)
        for migration in migrations:
            print(
                f"{migration.version}: {migration.description} "
                f"(SHA-256 {migration.checksum_sha256})"
            )
        print(f"Validated {len(migrations)} migration(s).")
        return 0

    with connect_database(url_env_var=MIGRATION_DATABASE_URL_ENV) as connection:
        applied = apply_migrations(connection, MIGRATIONS_DIR)

    if applied:
        print("Applied migrations: " + ", ".join(applied))
    else:
        print("No pending migrations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())