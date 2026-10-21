# Stage 2 — India Airport Master
## Purpose
Build a reproducible, validated reference subset of Indian airport records from the OurAirports `airports.csv` source. This dataset is intended for downstream airport matching and analytics.
It is not a complete inventory of all physical airports in India and does not independently establish operational status.
## Source and local files
- Source URL: https://ourairports.com/data/
- Local source: `data/reference/ourairports_airports.csv`
- Generated master: `data/processed/india_airport_master.csv`
- Generated report: `reports/airport_master_build_report.json`
- Builder module: `src/flight_intelligence/transforms/airport_master.py`
- CLI entry point: `scripts/build_airport_master.py`
- Unit tests: `tests/unit/test_airport_master.py`
The source and generated CSV are excluded from Git by `.gitignore`. Re-download the source from its publisher when refreshing the dataset, then rebuild the master.
## Inclusion and exclusion rules
The current master includes Indian (`iso_country = IN`) records with type:
- `large_airport`
- `medium_airport`
- `small_airport`
The following source types are excluded from this master but counted in the build report:
- `heliport`
- `closed`
- `seaplane_base`
These exclusions define the current analytical scope. They do not imply that every excluded facility is inactive or irrelevant.
## Validation
Candidate records are checked for:
- Missing source ID
- Missing or blank name
- Latitude outside -90 to 90, or non-numeric/missing latitude
- Longitude outside -180 to 180, or non-numeric/missing longitude
- Duplicate IDs among candidate records
Records failing one or more checks are rejected. The report counts each validation reason; a record with multiple errors can contribute to multiple error counts.
The source schema is checked before transformation. Missing required source columns cause the build to fail.
## Baseline build
Baseline observed on 2026-10-21:
- Worldwide source rows: 86,258
- India source rows: 654
- Large airport candidates: 43
- Medium airport candidates: 98
- Small airport candidates: 179
- Total candidates: 320
- Accepted master records: 320
- Rejected candidates: 0
- Scheduled service marked yes: 118
- Scheduled service marked no: 202
- Records with IATA code: 164
- Records with ICAO code: 180
These counts describe the downloaded source snapshot and can change when the source is refreshed. They are not targets or guarantees.
## Rebuild
From the repository root, with the project virtual environment activated:
```powershell
python .\scripts\build_airport_master.py
```
Optional arguments:
- `--source` — source CSV path
- `--output` — output master CSV path
- `--report` — output JSON report path
## Traffic tiers
This stage does not assign traffic tiers to airports. Tiers require reliable annual movement data and are handled separately by the configured tier-classification logic. T5 and T6 movement boundaries remain unresolved. T0 means unclassified or reliable traffic data unavailable, not zero traffic.
## Licensing and publication
The source licence and redistribution terms must be reviewed and recorded before public redistribution of the source or derived data. The presence of a public download URL alone is not sufficient evidence of permission to republish. Raw source data is not committed to this repository by default.
## Current limitations
- Airport records and names are derived from the downloaded source and have not all been independently verified.
- Scheduled-service flags are source metadata, not a guarantee of current operations.
- No live ADS-B coverage, collection success, or aircraft activity is established by this master.
- A successful schema and coordinate validation does not prove completeness, operational status, or licensing clearance.
