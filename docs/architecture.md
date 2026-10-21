# Architecture and implementation plan

## Current state
Stage 1 foundation only. External integrations, scheduled collection, database migrations, and dashboards are not implemented. The following describes the intended architecture.

## Logical flow
1. Source adapters retrieve airport reference data, ADS-B observations, official reports, and weather.
2. Raw landing records provenance, retrieval time, source timestamps, query scope, and run ID. Raw data remains private by default.
3. Validation and normalization check schema, coordinates, timestamps, IDs, duplicates, and source-specific rules.
4. Storage persists reference data, observation facts, collection attempts, quality outcomes, and pipeline runs.
5. Analytics creates qualified airport activity and official-statistic aggregates.
6. Publication exports approved aggregates atomically, preserving last known-good output after failures.
7. Dashboards show definitions, cohort, period, freshness, coverage, and limitations.

## Planned infrastructure
Python package in `src/flight_intelligence`; PostgreSQL-compatible storage (Neon planned); GitHub Actions (subject to provider limits); Vercel for server-side API/dashboard; Apache ECharts for charts.

## Timestamp and source separation
Every observation should distinguish `source_type` (`live_poll` or `archive_sample`), `source_observed_at`, `retrieved_at`, `ingested_at`, `pipeline_run_id`, `source_name`, and `query_scope`. Archive samples must never be shown as current live observations.

## Airport assignment policy
Initial rule: 30 nautical mile candidate radius; airborne altitude ceiling 5,000 ft above airport elevation; explicit ground status may qualify on-ground aircraft within the geofence. Unknown altitude is excluded from airborne eligibility unless explicit ground status supports on-ground eligibility. Missing coordinates remain unassigned; missing elevation prevents elevation-based airborne eligibility. If multiple airports qualify, assign the nearest eligible airport with documented tie tolerance and stable airport ID. Store distance, altitude, eligibility reason, and rule version. Later compare 20 vs 30 nm and 3,000 vs 5,000 ft.

## Failure behavior
Bounded retries for transient errors; record failures without secrets; enforce request/payload budgets; stop when quota guard trips; publish aggregate snapshots atomically; preserve last known-good output on failure. Show latest source observation, latest successful pipeline run, and latest public-data update separately.
