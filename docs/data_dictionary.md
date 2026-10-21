# Data dictionary (starter contract)

## Airport reference
- `airport_id`: stable project identifier.
- `source_airport_id`: original source identifier.
- `name`, `iata_code`, `icao_code`: source name/codes where available.
- `latitude`, `longitude`: WGS84 coordinates.
- `elevation_ft`: airport elevation, nullable.
- `country_code`: country code used in documented filtering.
- `source_name`, `source_url`, `retrieved_at`: provenance.
- `record_status`, `validation_errors`: validation/filter disposition.

## ADS-B observation
- `observation_id`: internal row identifier.
- `source_name`: provider.
- `source_type`: `live_poll` or `archive_sample`.
- `source_observed_at`: provider timestamp in UTC, when supplied.
- `retrieved_at`, `ingested_at`: retrieval and persistence timestamps in UTC.
- `aircraft_id`: stable provider aircraft identifier when available; callsign alone is not a stable key.
- `callsign`: optional mutable flight/callsign string.
- `latitude`, `longitude`, `altitude_ft`, `on_ground`: position fields, nullable as appropriate.
- `airport_id`: assignment result, nullable.
- `assignment_rule_version`, `query_scope`, `pipeline_run_id`: assignment and provenance.

## Collection run
Record run ID, source, start/end time, outcome, request/response counts, error categories, quota status, and software/config version.

## Official statistics
Record source report ID and URL, publication date, reporting period, airport/airline identifier, metric, value, unit, source page/table, retrieval time, and reconciliation status.

## Weather observation
Record provider/station ID, station coordinates, observation/retrieval timestamps, variable/value/unit, quality flags, source URL, and station distance if calculated.

Persist timestamps in UTC; convert to `Asia/Kolkata` for display. Never infer a time zone for naive timestamps without a documented source rule.
