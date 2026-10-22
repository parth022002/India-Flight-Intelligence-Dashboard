# Scripts
Scripts are added only after their inputs, source terms, outputs, dry-run behavior, request budgets, and tests are defined.
## Implemented scripts
- `build_airport_master.py` - builds the validated India airport master.
- `apply_migrations.py` - applies database migrations with an explicit migration database URL.
## Planned scripts
- `classify_airport_traffic.py`
- `audit_adsb_coverage.py`
- `collect_adsb.py`
- `collect_weather.py`
- `ingest_official_reports.py`
- `process_adsb_archive.py`
- `assign_airports.py`
- `validate_data.py`
- `build_aggregates.py`
- `build_density_grid.py`
- `apply_retention.py`
- `export_public_data.py`
## ADS-B collection status
The ADS-B client and orchestrator have unit and PostgreSQL integration tests. A dedicated collection runner is not yet implemented. Live collection remains disabled until the provider's current access requirements, licensing obligations, and permitted usage limits have been reviewed and approved.
Project-side request and payload caps are not provider-approved limits. Raw payload publication and the public API remain disabled by default.
