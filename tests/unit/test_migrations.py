import hashlib
from pathlib import Path

import pytest

from flight_intelligence.storage.migrations import (
    Migration,
    _migration_body,
    discover_migrations,
)


def test_discover_migrations_orders_by_numeric_version(tmp_path: Path) -> None:
    (tmp_path / "002_add_indexes.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / "001_initial_schema.sql").write_text("SELECT 1;", encoding="utf-8")
    migrations = discover_migrations(tmp_path)
    assert [migration.version for migration in migrations] == ["001", "002"]
    assert [migration.description for migration in migrations] == [
        "initial schema",
        "add indexes",
    ]
def test_migration_checksum_is_sha256_of_file_contents(tmp_path: Path) -> None:
    contents = "SELECT 1;"
    (tmp_path / "001_initial_schema.sql").write_text(contents, encoding="utf-8")
    migration = discover_migrations(tmp_path)[0]
    assert migration.checksum_sha256 == hashlib.sha256(
        contents.encode("utf-8")
    ).hexdigest()
def test_discover_migrations_rejects_invalid_filename(tmp_path: Path) -> None:
    (tmp_path / "initial.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid migration filename"):
        discover_migrations(tmp_path)
def test_discover_migrations_rejects_empty_file(tmp_path: Path) -> None:
    (tmp_path / "001_initial_schema.sql").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        discover_migrations(tmp_path)
def test_discover_migrations_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        discover_migrations(tmp_path / "missing")
def make_migration(contents: str, tmp_path: Path) -> Migration:
    path = tmp_path / "001_test.sql"
    return Migration(
        version="001",
        description="test",
        checksum_sha256=hashlib.sha256(contents.encode("utf-8")).hexdigest(),
        contents=contents,
        path=path,
    )
def test_migration_body_removes_transaction_wrappers(tmp_path: Path) -> None:
    migration = make_migration("BEGIN;\nSELECT 1;\nCOMMIT;", tmp_path)
    assert _migration_body(migration) == "SELECT 1;"
def test_migration_body_rejects_missing_begin(tmp_path: Path) -> None:
    migration = make_migration("SELECT 1;\nCOMMIT;", tmp_path)
    with pytest.raises(ValueError, match="must start with BEGIN"):
        _migration_body(migration)
def test_migration_body_rejects_missing_commit(tmp_path: Path) -> None:
    migration = make_migration("BEGIN;\nSELECT 1;", tmp_path)
    with pytest.raises(ValueError, match="must end with COMMIT"):
        _migration_body(migration)
