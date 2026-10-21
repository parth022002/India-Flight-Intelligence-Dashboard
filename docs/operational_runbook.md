# Operational runbook

## Local development (Windows PowerShell)
```powershell
Set-Location "C:\Users\parth\OneDrive\Desktop\India Flight Intelligence"
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m compileall src scripts
```
If activation is blocked, do not weaken system-wide execution policy; call `\.venv\Scripts\python.exe` directly.

## Configuration
Copy `config/settings.example.json` to `config/settings.local.json`. Keep local settings and secrets out of Git. Collection stays disabled until source terms, limits, and fixtures are reviewed.

## Before collection
Review source terms/attribution, request scope, timeouts, retries, rate limits, free-tier quotas, raw-data access, schema fixtures, and dry-run behavior.

## Failure handling
Log error categories and run IDs while redacting secrets. Retry only transient failures with bounded backoff. Do not replace good output with empty output after a failed run. Preserve last known-good aggregates and investigate schema changes, stale data, and quota warnings.

## Git safety
Inspect `git status --short` before staging. Never stage secrets, local datasets, or unrelated files. Avoid `git clean`, `git reset --hard`, and broad restore commands as routine troubleshooting.

## Database operations (Stage 3)

### Verified baseline
- Neon PostgreSQL connectivity has been verified using the local `DATABASE_URL` environment variable.
- Migration `001` (`initial schema`) is recorded in `schema_migrations`.
- The India airport master contains 320 records under the stored scope `india_civil_airports_v1`.
- No duplicate `(source_name, source_airport_id)` keys were found during verification.
- The airport master importer validates the complete CSV before database writes and defaults to dry-run mode.
- A deliberate database constraint failure in an isolated temporary schema confirmed that the import transaction rolls back both the collection-run record and airport inserts.
- The migration was successfully applied to an isolated temporary schema, where all seven expected tables were verified.

These checks describe the verified baseline at the time of testing. Re-run the checks after relevant schema or importer changes.

### Migration safety
1. Review migration SQL and confirm it has a new, correctly ordered version.
2. Back up or otherwise establish a recovery plan before applying production changes.
3. Apply migrations through the repository migration runner.
4. Verify migration history, expected tables, constraints, indexes, and triggers afterward.
5. Never edit an already-applied migration. Add a new migration for schema changes.
6. Test destructive or failure scenarios in an isolated schema, not in `public`.

### Airport master import
- Validate the generated airport master before importing.
- Use dry-run mode to check the input without database writes.
- Run the actual import only after validation succeeds.
- Verify imported record counts, source-key uniqueness, and the stored country and scope values.
- Treat `records_upserted` as the number of records processed by the upsert operation; it does not distinguish inserts from updates.
- Confirm that a failed import leaves no partial collection-run or airport records.

### Database access and secrets
- Keep `DATABASE_URL` in the local `.env` file or an approved deployment secret store. Never commit or print credentials.
- The development connection currently uses `neondb_owner`, a broadly privileged role. Do not expose this credential in browser code or a public client.
- Before deploying an application or public API, design and test separate least-privilege access for ingestion and read-only approved aggregates.
- Do not grant public access to raw ADS-B observations or unrestricted database tables.
- Review effective role memberships, table privileges, schema privileges, and sequence/function permissions before deployment.
- Do not change production grants until the intended deployment access model has been reviewed and tested.

### Outstanding Stage 3 work
- Automate the real-PostgreSQL rollback test in an opt-in integration-test suite using an isolated temporary schema.
- Define and verify least-privilege roles for ingestion and approved aggregate reads before application deployment.
- Review database access and migration procedures before enabling scheduled collection or public serving.
