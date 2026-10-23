
# India Airport Coverage Verification

## Objective

Assess the coverage and data quality of the OurAirports-derived India airport master and extended aviation-facilities inventory using independent references.

The objective is to identify verified matches, possible omissions, conflicting records, and unresolved cases. No single source is assumed to represent every aviation facility in India.

## Local baselines

- Core airport master: `data/processed/india_airport_master.csv`
- Extended facilities: `data/processed/india_aviation_facilities.csv`
- Core build report: `reports/generated/airport_master_build_report.json`
- Extended build report: `reports/generated/aviation_facilities_build_report.json`

Observed local snapshot baseline on 2026-10-23:
- Core airport master: 320 records
- Extended facilities: 654 records
- Extended source types: large, medium, and small airports; heliports; seaplane bases; and records classified by the source as closed

These are source-derived counts, not proof of national completeness.

## Independent references

### Airports Authority of India airport list

URL: https://www.aai.aero/en/business-opportunities/indian-airports

The page displays an update date of 23 June 2020. Use it as a supplementary name-matching reference. Its age must be considered when evaluating current coverage.

### India eAIP - licensed public-use aerodromes

URL: https://aim-india.aai.aero/eaip/eaip-v2-05-2025/eAIP/IN-AD%201.5-en-GB.html

Use this reference to check the licensing information it publishes, including ICAO location indicators and licence validity details. A licensed public-use aerodrome list is not a complete list of all heliports, private facilities, or other aviation sites.

### Ministry of Civil Aviation airport documents

URL: https://www.civilaviation.gov.in/ministry-documents/airports-documents

Use these documents as supplementary evidence for airport developments and projects. Distinguish proposed, under-construction, licensed, and operational facilities where the source provides enough evidence to do so.

## Matching and evidence rules

- Match exact identifiers first where comparable identifiers exist.
- Use normalized names and geographic context to generate possible matches when identifiers are absent.
- Treat name-only matches as candidates for review, not confirmed matches.
- Record source title, URL, publication/update date when available, access date, and relevant evidence for every comparison.
- Classify results as matched, possible match, reference-only candidate, conflicting evidence, or unresolved.
- Do not infer that a facility is nonexistent because it is absent from one reference.
- Do not infer current operations solely from an OurAirports source type or scheduled-service flag.
- Do not classify proposed projects as operational airports without supporting evidence.

## Constraints

- Do not modify the existing airport master or extended inventory during the initial audit.
- Do not import the extended inventory into PostgreSQL.
- Do not enable live ADS-B collection.
- Review source licensing and redistribution conditions before publishing source-derived data.
- Document limitations and unresolved cases before claiming coverage completeness.
## Historical AAI reference extraction
A local copy of the AAI `LIST OF AIRPORTS` PDF is used as a supplementary historical name-matching reference.
- Source file: `data/reference/aai_airports/list_of_airports_aai_2020.pdf`
- Reference date: 2020-06-23, based on the update date displayed on the AAI webpage; this is not confirmed as the PDF's publication date.
- Parser: `src/flight_intelligence/transforms/aai_airport_reference.py`
- Generated output: `data/reference/aai_airports/aai_airport_reference.csv`
- Extracted records: 153.
The extracted classification counts reconcile with the document summary:
- International: 26 `INTL` + 3 `INTL(CE)` = 29.
- Customs: 10 `CUS`.
- Domestic: 91 `DOM` + 23 `DOM(CE)` = 114.
- The document summary reports 153 airports for international plus domestic; customs is a separate category and must not be added to that total again.
These are parser-level structural checks, not independent verification of every airport name, owner, or status against the PDF. The `OPS` and `NON-OPS` values are historical source claims, not verified current operating status.
The repository's `.gitignore` rule `data/reference/*` excludes the source PDF, extracted layout text, and generated CSV. The generated reference therefore remains local unless repository inclusion is deliberately reviewed and approved.
