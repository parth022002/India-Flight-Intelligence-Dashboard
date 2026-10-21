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
