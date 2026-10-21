# Delivery stages

1. Foundation: environment, repository, configuration, logging, tests, docs, licensing register.
2. Airport master and tiers: retrieve source, validate/filter, count inclusions/exclusions, resolve T5/T6 boundaries.
3. Database schema: migrations, contracts, security, provenance.
4. ADS-B collector: provider implementation, bounded pilot, rate-limit and feasibility audit.
5. Airport assignment/activity analytics: geofence, altitude, deduplication, fixed-slot metrics.
6. Historical archive proof of concept: license-aware sample, separate source type, assess up to 12 sample days if feasible.
7. Official statistics: ingest verified reports and reconcile matched periods/cohorts.
8. Weather: verify coverage and terms, ingest observations.
9. KPIs and aggregates: tested definitions, quality and share-residual analysis.
10. Public application: approved aggregate API and four dashboards.
11. Automation and operations: schedules, monitoring, retention, quota guards, recovery.
12. Final validation and release: tests, security, licensing, documentation, public-release checklist.

Completion is evidence-based; placeholder files alone do not complete a stage.
