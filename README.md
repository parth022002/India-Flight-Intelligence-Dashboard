# India Flight Intelligence

A free-first data engineering and analytics project designed to improve visibility into Indian airport activity using airport reference data, ADS-B observations, verified official aviation statistics, and weather observations where available.

> **Status: Stages 1-2 implemented; Stage 3 pending.** The repository foundation, validated airport reference-master builder, and initial traffic-tier classification logic are implemented and tested. Database integration, live ADS-B collection, nationwide coverage validation, and dashboards are not yet implemented. This project does not claim live coverage until capabilities are built and validated.

## Objectives
- Build a documented airport reference master from validated public records.
- Attempt ADS-B collection while tracking per-airport coverage, freshness, and provenance.
- Keep `live_poll` observations separate from `archive_sample` observations.
- Ingest official statistics only when the source and reuse terms are verified.
- Integrate weather observations where coverage and terms allow.
- Publish approved aggregate metrics without exposing raw aircraft-level data or secrets.
- Make data quality, limitations, and pipeline health visible.

## Planned dashboards
1. Airport Activity & ADS-B Observability
2. Official Traffic & Airline Performance
3. Weather & Seasonal Patterns
4. Data Quality, Pipeline & Alerts

## Planned technology
Python, PostgreSQL (Neon planned), GitHub Actions, Vercel, and Apache ECharts. Tableau Public may be supplementary. These integrations are plans, not yet configured capabilities.

## Local setup (Windows PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```
If `.venv` already exists and is activated, do not recreate it; run only relevant install/test commands.

## Configuration
Copy `config/settings.example.json` to `config/settings.local.json` for local overrides. Never commit local settings, credentials, `.env`, or secrets. Collection is disabled by default. T5/T6 movement boundaries are unresolved in `config/thresholds.json`; do not invent cutoff values or classify those tiers until an evidence-backed boundary is approved.

## Interpretation guardrails
- The airport master is the set of records passing documented validation/filter rules, not every physical airfield in India.
- ADS-B collection attempts do not guarantee observations; provider access, receiver coverage, traffic, query scope, rate limits, and scheduling affect results.
- Missing observations/time slots are missing, not zero.
- ADS-B does not establish official arrivals/departures, cancellations, or delays.
- Archive samples are not current live observations.
- Publish approved aggregates only; raw aircraft-level data is private by default.

See `docs/` for architecture, KPI definitions, lineage, dashboard requirements, retention, and operations.

## Security, cost, and licensing
Never commit API keys, database URLs, tokens, or raw payloads. Keep credentials server-side. Monitor free-tier quotas and do not enable paid upgrades without explicit approval. Public URLs do not imply unrestricted reuse; review `NOTICE.md` and `config/source_licences.csv`.

## Development
```powershell
python -m pytest
python -m compileall src scripts
```

## License
Repository code is licensed under MIT; third-party datasets and services retain their own terms. See `LICENSE` and `NOTICE.md`.
