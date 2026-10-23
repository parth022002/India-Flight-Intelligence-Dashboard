# Scripts

Scripts are added only after their inputs, source terms, outputs, dry-run behavior, request budgets, and tests are defined.

## Implemented scripts

- `build_airport_master.py` — builds the validated India airport master.
- `build_aviation_facilities.py` — builds the extended aviation facilities inventory.
- `apply_migrations.py` — validates and applies database migrations with an explicit migration database URL.
- `collect_adsb.py` — provides a guarded ADS-B collection runner with a dry-run mode. Dry-run validation does not connect to the database or make network requests.

## Planned scripts

The following standalone scripts are not currently present in the `scripts` directory:

- `classify_airport_traffic.py`
- `audit_adsb_coverage.py`
- `collect_weather.py`
- `ingest_official_reports.py`
- `process_adsb_archive.py`
- `assign_airports.py`
- `validate_data.py`
- `build_aggregates.py`
- `build_density_grid.py`
- `apply_retention.py`
- `export_public_data.py`

Some related functionality may exist in package modules; a missing standalone script does not by itself establish that the entire feature is absent.

## ADS-B collection status

The ADS-B client, normalizer, orchestrator, persistence layer, and collection runner are implemented. Unit tests and PostgreSQL integration tests cover parts of this workflow.

The full project test suite and Ruff checks have passed in the current local validation baseline. These results establish tested software behavior, not provider permission or production readiness.

Live collection and public release remain **not approved**. Keep the example configuration settings unchanged:

- `collection.enabled`: `false`
- `adsb.enabled`: `false`
- `adsb.pilot_mode`: `true`
- Raw payload publication and public API access remain disabled by default.

Before any live pilot, resolve the provider's licensing obligations, access requirements, permitted request limits, retention and redistribution rules, and formal approval conditions.

Project-side request and payload caps are safeguards, not provider-approved limits. The current request budgets apply within an individual client instance; they do not establish a global quota across concurrent processes or repeated runs.

## Known implementation gaps

- The normalizer currently leaves `observed_at` unset because a documented source timestamp mapping has not been established.
- Airport assignment and aggregate generation still require implementation verification.
- Automated retention enforcement is not implemented in the reviewed Python source tree.
- Provider compliance, operational limits, effective deployment configuration, and pilot authorization remain unresolved.

Do not enable live collection, publish raw observations, or implement destructive retention actions until the applicable approvals and safeguards are in place.
