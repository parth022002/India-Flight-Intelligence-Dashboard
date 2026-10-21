# KPI definitions and interpretation guardrails

## Observability
- **Latest source observation:** maximum valid provider observation timestamp for the stated source/cohort.
- **Last successful pipeline run:** latest completed successful run; distinct from source freshness.
- **Last public data update:** publication time of the snapshot currently served.
- **Collection attempt success rate:** successful eligible attempts divided by all eligible attempts in the period; disclose denominator and exclusions.
- **Coverage:** explicitly name the denominator (validated airports, eligible airports, queried airports, or airports with observations).

## Aircraft activity
Where sampling supports it, use fixed 10-minute aircraft-slot bins. Count a stable aircraft identifier at most once per slot under documented deduplication. Do not deduplicate by callsign alone. Missing slots are missing, not zero. ADS-B sample counts are not total aircraft movements.

## Official reconciliation
Use official movements only for their documented period, airport cohort, and metric definition. A matched-cohort share residual may be defined as `observed_ADSB_share - official_movement_share`, in percentage points. Call it a **share residual**, not capture rate. For archive sample days, report mean, standard deviation, eligible day count, and bootstrap interval only when sample size/design support it. Do not infer official arrivals, departures, cancellations, OTP, or delays from ADS-B positions alone.

## Quality
Track schema failures, missing IDs/coordinates/timestamps, duplicate candidates, unassigned positions, stale sources, and reconciliation failures with denominators and time windows. Charts/API responses should include metric version, cohort, time window, freshness, and limitations where material.
