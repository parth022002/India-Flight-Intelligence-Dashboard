
# India Aviation Facilities Inventory

## Purpose

Build a reproducible reference inventory of Indian aviation facilities from the local OurAirports `airports.csv` source. This dataset extends the facility categories represented in the core airport master.

It is a source-derived inventory, not a complete or independently verified inventory of every physical or operational aviation facility in India.

## Source and output files

- Source URL: https://ourairports.com/data/
- Local source: `data/reference/ourairports_airports.csv`
- Generated inventory: `data/processed/india_aviation_facilities.csv`
- Generated report: `reports/generated/aviation_facilities_build_report.json`
- Builder module: `src/flight_intelligence/transforms/aviation_facilities.py`
- CLI entry point: `scripts/build_aviation_facilities.py`
- Unit tests: `tests/unit/test_aviation_facilities.py`

The source and generated CSV are excluded from Git by `.gitignore`. The build date records when the inventory was generated; it is not a verified publisher source-snapshot date.

## Scope

The builder selects source records with `iso_country = IN` and retains source facility types, including:

- `large_airport`
- `medium_airport`
- `small_airport`
- `heliport`
- `seaplane_base`
- `closed`

The source-reported `type` is preserved. In particular, `closed` is not an independently verified statement of current operational status.

This inventory is separate from `data/processed/india_airport_master.csv`. Do not pass it to the existing airport database importer: the extended dataset has a different scope and is not a replacement for the core airport master.

## Validation

The builder checks:

- Required source columns
- Missing or blank source ID, identifier, facility type, and name
- Non-numeric, missing, or out-of-range latitude and longitude
- Duplicate IDs among Indian candidate records

Records failing one or more checks are rejected. The report counts each validation reason; a record with multiple errors can contribute to multiple error counts.

Successful validation does not establish operational status, identifier authority, completeness, or coordinate accuracy beyond the checks described above.

## Baseline build

Observed on 2026-10-23 from the local source snapshot:

- Indian source records: 654
- Accepted facilities: 654
- Rejected candidates: 0
- Large airports: 43
- Medium airports: 98
- Small airports: 179
- Heliports: 302
- Closed-type records: 31
- Seaplane bases: 1

These counts describe the local source snapshot and can change when the source is refreshed. They are not national coverage targets or guarantees.

## Rebuild

From the repository root, with the project virtual environment activated:

```powershell
python .\scripts\build_aviation_facilities.py
```

Optional arguments:

- `--source` — source CSV path
- `--output` — output inventory path
- `--report` — output JSON report path

## Licensing and publication

Review the source licence and redistribution terms before publicly redistributing the source or derived data. A public download URL alone is not evidence of permission to republish. The generated inventory is not automatically approved for public distribution.

## Current limitations

- All records originate from one source snapshot and have not been independently verified.
- The inventory does not prove that all Indian aviation facilities are represented.
- Source facility type does not establish current operational status.
- Scheduled-service flags are source metadata, not a guarantee of current operations.
- This dataset does not establish live ADS-B coverage, collection success, or aircraft activity.
- Traffic tiers are not assigned by this builder.
