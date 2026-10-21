# Dashboard specifications (planned)

## 1. Airport Activity & ADS-B Observability
Answer which validated airports have recent observations, which are stale/unobserved/not queryable, and how observed aircraft-slot counts vary. Show period, cohort, source, source freshness, pipeline success time, publication time, coverage denominator, and missingness caveat.

## 2. Official Traffic & Airline Performance
Show official movement/passenger/freight trends and verified airline metrics. Cite authoritative sources and reporting periods. Do not fabricate metrics or derive OTP/cancellations from ADS-B.

## 3. Weather & Seasonal Patterns
Show available weather observations, station distance, observation time, coverage gaps, and association-versus-causation caveats. Avoid unreviewed safety labels.

## 4. Data Quality, Pipeline & Alerts
Show pipeline outcome, stale sources, schema failures, quota guardrails, severity definitions, timestamps, denominator, and remediation.

Shared UX: answer-first titles, clear units, readable trends, accessible labels, no misleading zeroes, source/freshness metadata, transparent uncertainty, and no raw aircraft-level public endpoints by default.
