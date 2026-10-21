"""Transactional PostgreSQL SQL migration runner."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

MIGRATION_FILENAME = re.compile(
    r"^(?P<version>\d{3,})_(?P<description>[a-z0-9_]+)\.sql$"
)
ADVISORY_LOCK_KEY = 731204681
@dataclass(frozen=True)
class Migration:
    """A discovered SQL migration."""
    version: str
    description: str
    checksum_sha256: str
    contents: str
    path: Path
def discover_migrations(directory: str | Path) -> list[Migration]:
    """Read and validate migration files in numeric version order."""
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"Migration directory not found: {root}")
    migrations: list[Migration] = []
    seen_versions: set[str] = set()
    for path in root.glob("*.sql"):
        match = MIGRATION_FILENAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"Invalid migration filename: {path.name}")
        version = match.group("version")
        if version in seen_versions:
            raise ValueError(f"Duplicate migration version: {version}")
        seen_versions.add(version)
        contents = path.read_text(encoding="utf-8-sig")
        if not contents.strip():
            raise ValueError(f"Migration file is empty: {path.name}")
        migrations.append(
            Migration(
                version=version,
                description=match.group("description").replace("_", " "),
                checksum_sha256=hashlib.sha256(
                    contents.encode("utf-8")
                ).hexdigest(),
                contents=contents,
                path=path,
            )
        )
    return sorted(migrations, key=lambda item: int(item.version))
def _migration_body(migration: Migration) -> str:
    """Validate and remove the migration's outer transaction wrappers."""
    body = migration.contents.strip()
    if not body.upper().startswith("BEGIN;"):
        raise ValueError(f"Migration {migration.path.name} must start with BEGIN;")
    if not body.upper().endswith("COMMIT;"):
        raise ValueError(f"Migration {migration.path.name} must end with COMMIT;")
    body = body[len("BEGIN;") :].strip()
    body = body[: -len("COMMIT;")].strip()
    if not body:
        raise ValueError(f"Migration {migration.path.name} has no SQL statements.")
    return body
def apply_migrations(
    connection: psycopg.Connection,
    directory: str | Path,
) -> list[str]:
    """Apply pending migrations atomically and reject changed migration files."""
    # Validate every file before opening any migration transaction.
    migrations = discover_migrations(directory)
    prepared = [(migration, _migration_body(migration)) for migration in migrations]
    applied_now: list[str] = []
    for migration, body in prepared:
        # The transaction-level lock is released automatically on commit or rollback.
        # It serializes concurrent runners without a separate unlock query.
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(%s)",
                    (ADVISORY_LOCK_KEY,),
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(100) PRIMARY KEY,
                        description TEXT NOT NULL,
                        checksum_sha256 CHAR(64) NOT NULL,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    SELECT checksum_sha256
                    FROM schema_migrations
                    WHERE version = %s
                    """,
                    (migration.version,),
                )
                existing = cursor.fetchone()
                if existing is not None:
                    if existing[0].strip() != migration.checksum_sha256:
                        raise ValueError(
                            f"Migration {migration.version} has changed after "
                            "application. Create a new migration instead."
                        )
                    continue
                cursor.execute(body, prepare=False)
                cursor.execute(
                    """
                    INSERT INTO schema_migrations
                        (version, description, checksum_sha256)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        migration.version,
                        migration.description,
                        migration.checksum_sha256,
                    ),
                )
        # Reached only after the transaction has committed successfully.
        applied_now.append(migration.version)
    return applied_now
