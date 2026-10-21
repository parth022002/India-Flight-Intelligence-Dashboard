# Retention policy

The tier-based month values apply only to **live ADS-B observations**.

| Tier | Target poll interval | Live ADS-B retention |
|---|---:|---:|
| T1 | 60 minutes | 6 months |
| T2 | 90 minutes | 8 months |
| T3 | 120 minutes | 10 months |
| T4 | 150 minutes | 12 months |
| T5 | 180 minutes | 14 months; boundary unresolved |
| T6 | 210 minutes | 16 months; boundary unresolved |
| T0 | 240 minutes | 18 months |

T0 means unclassified or reliable traffic data unavailable, not no traffic. T5/T6 must not be assigned until non-overlapping movement boundaries are approved.

Airport reference data, official reports, weather, logs, archive samples, and aggregates need separate policies based on analytical need, provider terms, privacy, and license. Implement deletion only with dry-run-first behavior, tests, audit records, and recovery planning.
