# India Flight Intelligence — National Aviation Intelligence Blueprint

**Document type:** Proposed product, data, and ADS-B pilot scope
**Version:** 1.0
**Status:** Draft — not approved for live collection
**Geographic focus:** India
**Primary objective:** Build a comprehensive airport intelligence platform with a near-real-time aircraft activity dashboard, subject to data availability, provider permission, and verified technical feasibility.

---

## 1. Executive vision

India Flight Intelligence aims to become an India-focused aviation analytics platform that combines a comprehensive airport reference catalogue, approved aircraft observations, historical activity, and analytical dashboards.

The platform should help users answer questions such as:

- Which Indian airports have the highest observed aircraft activity?
- How does observed activity differ by airport, region, and time of day?
- Which airports have sufficient data for reliable comparisons?
- How does activity change across days, weeks, and months?
- What proportion of the airport network has adequate reference data and observation coverage?
- Where are aircraft observations missing, stale, inconsistent, or insufficient?
- How confident should an analyst be in each reported metric?

The product must distinguish **observed aircraft activity** from actual airport traffic. ADS-B feeds may be incomplete, and an observed aircraft count is not automatically equivalent to departures, arrivals, passenger traffic, or official airport movement statistics.

The objective is not merely to display aircraft on a map. It is to create a trustworthy, explainable, and progressively more comprehensive aviation intelligence product for India.

## 2. Product principles

1. **India-first:** Indian airport coverage, Indian geographic context, and India-relevant analysis take priority.
2. **Airport completeness:** Maintain a traceable catalogue of airports and aerodromes within an explicitly defined scope.
3. **Evidence-based coverage:** Track which airports and regions have usable reference data and which have verified observation coverage.
4. **No invented statistics:** Every published metric must have a defined source, calculation, time window, and limitation.
5. **Near-real-time only when justified:** Display freshness and latency. Do not promise live or real-time coverage until it has been measured.
6. **Compliance before collection:** No provider access or publication permission is assumed from a public API, licence label, successful test, or code implementation.
7. **Privacy and minimum necessary data:** Collect and retain only fields justified by the approved use.
8. **Reproducibility:** Analytical results should be reproducible from documented source records, transformations, and metric definitions.
9. **Fail safely:** Missing or stale observations must not silently become zero traffic.
10. **Clear separation of evidence:** Official statistics, airport reference data, ADS-B observations, and model-derived estimates must remain distinguishable.

## 3. National airport coverage strategy

### 3.1 Establish a complete, auditable airport inventory

The project already records an India civil airport master of 320 records under the stored scope `india_civil_airports_v1`. This is a useful starting dataset, but that count must not be treated as proof that every Indian airport or aerodrome is represented.

The first goal is to establish the actual coverage of the catalogue, reconcile it against authoritative and appropriately reusable sources, and document exclusions.

The inventory should evaluate these categories separately:

- International airports.
- Domestic commercial airports.
- Airports with scheduled passenger services.
- Airports with non-scheduled or limited civil operations.
- Regional connectivity and UDAN-related airports, where applicable.
- Civil enclaves and shared-use facilities.
- General aviation and other civil aerodromes.
- Heliports, where included in the agreed scope.
- Water aerodromes, where included in the agreed scope.
- Temporarily closed, permanently closed, or proposed facilities.
- Defence-only facilities, which require a separate scope and source-permission assessment.

These are catalogue categories, not a claim that every category is already covered or that each facility is currently operational.

### 3.2 Define what “all airports in India” means

For acceptance purposes, use a declared **national civil airport and aerodrome inventory scope** rather than an unqualified claim of universal completeness.

The scope should explicitly state:

- Which facility types are included.
- Whether heliports and water aerodromes are included.
- How civil enclaves are represented.
- Whether closed and proposed facilities are retained for historical or planning purposes.
- Whether defence-only facilities are excluded.
- What constitutes a unique facility.
- How duplicates, aliases, airport renamings, and changes of operator are handled.
- The source and last verification date for each important attribute.

Do not remove a facility simply because it has no ADS-B observations. Catalogue membership and aircraft observation availability are separate concepts.

### 3.3 Airport identity and reference fields

The airport catalogue should support the following fields when available and permitted:

| Field group | Proposed fields |
|---|---|
| Identity | Stable internal airport ID, canonical name, known aliases |
| Codes | ICAO code, IATA code, other source identifiers |
| Location | Latitude, longitude, elevation, coordinate reference |
| Geography | State or union territory, district where available, region |
| Facility type | Airport, aerodrome, heliport, water aerodrome, or other defined category |
| Operational status | Operational, temporarily closed, permanently closed, proposed, or unknown |
| Civil use | Civil, civil enclave, shared use, or other approved classification |
| Service profile | Scheduled passenger service, other known civil activity, or unknown |
| Source lineage | Source name, source record ID, source URL, import batch |
| Verification | Last verified date, verification method, confidence or quality flags |
| Change history | Previous values, effective dates where known, reason for change |

Do not fabricate missing IATA or ICAO codes, operating status, passenger volumes, runway characteristics, or service schedules. Unknown values must remain explicitly unknown.

### 3.4 Airport reconciliation and quality control

Create a repeatable process to:

1. Import each approved source into a staging area.
2. Validate required columns, data types, coordinates, and source identifiers.
3. Detect duplicate source records and possible duplicate facilities.
4. Reconcile aliases and identifiers without merging facilities solely because their names are similar.
5. Compare counts and coverage across sources.
6. Record unresolved conflicts for manual review.
7. preserve source provenance and the history of changes.
8. Produce a coverage report showing matched, unmatched, duplicate, incomplete, and unverified records.
9. Publish a versioned master only after validation.

Airport counts should always state the facility scope, source version, and effective date.

## 4. Data-source strategy

Each source must have its own documented terms, provenance, access conditions, and permitted use.

### 4.1 Airport reference data

Use the existing airport master as the starting point. Evaluate additional authoritative airport and aerodrome reference sources to identify gaps, but do not assume that an official website grants unrestricted permission to extract or redistribute every dataset it hosts.

The OurAirports register entry records a provider-stated public-domain position. The exact dataset, source provenance, accuracy limitations, and intended redistribution must still be checked.

### 4.2 ADS-B observations

The current candidate provider is adsb.lol.

The project records ODbL 1.0 as provider-stated, but attribution, share-alike, database rights, retention, API access, production request limits, and publication obligations remain under review.

Before live collection, document:

- The approved API route and geographic query design.
- Permitted usage and access requirements.
- The intended coverage and refresh interval.
- Expected request count and response volume.
- The fields to be retained.
- Raw and transformed data retention rules.
- Attribution placement and redistribution requirements.
- The permitted use of aggregates and dashboard outputs.
- Provider responses, conditions, and the final approval decision.

Until these points are resolved, use local fixtures and mocked responses only.

### 4.3 Official traffic statistics

Evaluate suitable AAI, DGCA, and other official publications for airport-level passenger traffic, aircraft movements, and cargo statistics where available.

For each dataset, record the exact publication, owner, reporting period, unit of measurement, methodology, publication date, reuse conditions, and any third-party restrictions.

Official movement statistics and ADS-B-derived observations must remain separate measures. They may be compared only when the definitions, periods, and coverage are sufficiently compatible.

### 4.4 Weather and supporting data

Weather observations may provide future analytical context, but they should be integrated only after the relevant API terms, station coverage, historical access, attribution, and retention conditions are reviewed.

Weather should not be a prerequisite for the initial airport catalogue or basic activity dashboard.

## 5. Proposed data architecture

The target architecture should separate reference data, source observations, analytical transformations, and dashboard-ready outputs.

**Logical flow:**

1. Approved source register and configuration.
2. Source adapters and ingestion controls.
3. Validation, normalization, and source lineage.
4. Airport identity resolution and geographic association.
5. Controlled observation storage.
6. Data-quality checks and freshness monitoring.
7. Aggregation and metric calculation.
8. Approved analytical views or serving layer.
9. Dashboard, maps, filters, and report exports where permitted.
10. Audit records, monitoring, and operational review.

This is a target design, not a statement that every component has already been implemented.

### 5.1 Data-layer separation

**Airport reference layer**

Stores airport identities, locations, classifications, provenance, and verification history.

**Observation layer**

Stores only approved aircraft observations and the minimum necessary fields. Source timestamps, ingestion timestamps, and observation quality must be distinguishable.

**Analytical layer**

Stores or calculates approved airport/time-window metrics, coverage indicators, and data-quality summaries.

**Presentation layer**

Serves only outputs permitted by the applicable source terms and the project's publication decision.

Raw observations must not be exposed through the public API merely because they are available internally.

### 5.2 Observation timestamps

A trustworthy near-real-time product needs to distinguish:

- Provider-reported observation time, when supplied and interpretable.
- Ingestion time.
- Processing time.
- Aggregation window.
- Last successful collection time.

If a source record does not provide a reliable observation timestamp, the platform must not invent one or present ingestion time as if it were the aircraft observation time.

The current normalizer's `observed_at` field has been identified as unpopulated. This is an explicit limitation to resolve before making claims about observation age or precise historical movement.

### 5.3 Airport association

A flight observed near an airport is not automatically an arrival or departure.

Airport association should use a documented method and preserve uncertainty. Any future arrival/departure inference must define its geographic thresholds, trajectory requirements, time windows, edge cases, and validation against an appropriate reference.

Airport activity metrics should identify whether they represent:

- Aircraft observed in a geographic area.
- Distinct aircraft observed during a window.
- Inferred airport-associated movements.
- Officially reported airport movements.

These measures must not be combined under one ambiguous label.

## 6. Dashboard vision

The dashboard should tell an analytical story, not simply present a collection of charts.

### Dashboard 1 — National Aviation Overview

**Primary question:** What does the available evidence tell us about aviation activity across India?

Proposed components:

- KPI: airports in the approved master catalogue.
- KPI: airports with usable observations in the selected window.
- KPI: distinct aircraft observed, with the counting method stated.
- KPI: latest successful ingestion time and data freshness.
- India map showing airport locations and observation coverage.
- Regional comparison of observed activity.
- Activity trend over the selected period.
- Data coverage and quality indicator.
- Dynamic insight text that distinguishes real changes from missing data.

Every KPI should have a clear definition, unit, source, time window, and freshness indicator.

### Dashboard 2 — Airport Intelligence

**Primary question:** How does observed activity vary among Indian airports?

Proposed features:

- Searchable airport selector.
- Airport identity, codes, state, and facility type.
- Observation availability and data freshness.
- Activity trend for selected periods.
- Comparison with selected airports of similar scope.
- Available official passenger or movement statistics displayed separately.
- Airport reference completeness and verification status.

Airports with missing observations should be shown as **no usable data** rather than zero activity.

### Dashboard 3 — Regional Aviation Analysis

**Primary question:** How is observed activity distributed across India's regions?

Proposed features:

- State and region filters.
- Regional airport coverage.
- Observed activity by region and period.
- Comparison of data completeness across regions.
- Regional trend charts with consistent units and windows.
- Explicit warning when uneven provider coverage limits comparisons.

Regional rankings should not imply that low-observation regions have low actual traffic.

### Dashboard 4 — Activity and Temporal Trends

**Primary question:** How does observed aircraft activity change over time?

Proposed features:

- Hourly, daily, and weekly aggregations where timestamp quality permits.
- Time-of-day and day-of-week patterns.
- Distinct observed aircraft and observation counts as separate measures.
- Trend comparisons across consistent periods.
- Missing-data and coverage overlays.
- Annotations for source changes or known collection interruptions.

Do not label inferred movements as official flight counts.

### Dashboard 5 — Data Quality and Coverage

**Primary question:** Can we trust the current data enough to make a comparison?

Proposed features:

- Airports in scope versus airports with usable observations.
- Last successful ingestion and processing time.
- Missing and invalid coordinate rates.
- Missing timestamp rate.
- Duplicate observation indicators.
- Stale-data indicators.
- Source or schema changes.
- Provider errors and quota warnings.
- Coverage changes between periods.
- Unresolved airport identity matches.

This dashboard is essential: it prevents visually impressive charts from creating unjustified confidence.

### Dashboard 6 — Source and Compliance Status

**Primary question:** Which sources and outputs are approved for use?

Proposed features:

- Source review status.
- Licence and terms review date.
- Access and usage-limit approval status.
- Approved retention and deletion rules.
- Permitted output categories.
- Outstanding review actions.
- Clear distinction between development, pilot-approved, and production-approved sources.

This dashboard must not expose credentials, private correspondence, or sensitive operational details.

## 7. Metric dictionary and analytical rules

Every metric must be defined before publication.

| Metric | Definition and required caution |
|---|---|
| Airports in catalogue | Count of unique facilities within the declared inventory scope |
| Airports with usable observations | Distinct facilities meeting documented data-quality and freshness criteria |
| Distinct observed aircraft | Count of distinct permitted aircraft identifiers within a defined window; not necessarily total flights |
| Observation volume | Count of valid observation records after documented deduplication |
| Observation freshness | Time since the most recent valid source observation, when its timestamp is reliable |
| Ingestion freshness | Time since the last successful data ingestion |
| Airport observation coverage | Airports with usable observations divided by airports in the declared comparison scope |
| Regional observation activity | Defined observed-aircraft or observation measure aggregated consistently by region |
| Data completeness | Percentage of records satisfying required-field and validation rules |
| Inferred movements | Separately labelled estimates produced by a validated method; never presented as official movements |
| Official passenger or movement statistics | Source-reported measure with source, reporting period, and methodology preserved |

Avoid undefined metrics such as “live flights,” “airport traffic,” or “flight count” when the underlying calculation is actually an ADS-B observation count.

## 8. Proposed ADS-B pilot boundaries

The pilot is intended to test whether an informative, broad-India dashboard is technically and legally feasible.

### Proposed scope

- Geographic ambition: broad coverage across India.
- Initial analytical objective: an informative, near-real-time dashboard.
- Data acquisition: provider-approved geographic queries only.
- Storage: only fields and durations approved by the provider review.
- Publication: approved aggregates only, subject to the final compliance decision.
- Validation: mocked responses and local fixtures until authorization.
- Operational mode: explicitly bounded, monitored, and stoppable.

### Important feasibility condition

Broad national coverage may require multiple geographic queries or repeated retrieval over time. The existing example configuration allows at most two request attempts per runner invocation and a 5 MB cumulative response payload budget. Retries count as request attempts. The application-wide settings are configuration ceilings, not shared runtime counters.

These settings do not establish that broad-India coverage is feasible. The request geometry, refresh schedule, expected responses, provider quotas, and cumulative limits must be evaluated together before any pilot is proposed for execution.

Do not simply raise the request limits to make the national scope appear feasible.

### Frequency and request budget

The polling interval remains **TBD pending provider guidance and feasibility analysis**.

Before selecting an interval, estimate:

- Number of geographic queries per complete coverage cycle.
- Number of requests per cycle, including retries.
- Expected response size per query.
- Maximum and typical payload volume.
- Time needed to complete a cycle.
- Whether results are sufficiently fresh to support the intended dashboard.
- How incomplete cycles will be represented.
- How concurrent or repeated executions will be prevented from exceeding agreed limits.

If the available budget cannot support the proposed coverage, revise the coverage or refresh objective rather than silently exceeding the budget.

## 9. Retention, deletion, and data governance

The existing tier-based retention values are proposals, not approved retention permissions.

Before collection:

1. Confirm provider-specific retention permissions for raw and transformed observations.
2. Approve the data contract and required fields.
3. Resolve the T5/T6 movement boundaries before assigning those tiers.
4. Define deletion scope and whether derived outputs inherit any restrictions.
5. Define audit records, dry-run reporting, recovery planning, and deletion verification.
6. Test deletion behavior in an isolated environment before considering operational use.
7. Document who can approve changes and how the decision is reviewed.

Do not implement destructive retention jobs while provider permissions and data contracts remain unresolved.

Airport reference data, official reports, weather observations, application logs, and derived aggregates require their own retention rules.

## 10. Operational safeguards

Before any authorized pilot, the design must address:

- Explicit collection enablement and source approval.
- Provider-approved request and access limits.
- Per-invocation request and payload budgets.
- Cumulative limits across repeated runs if required.
- Bounded timeouts and retries.
- Safe handling of rate-limit and quota responses.
- Schema validation and unexpected payload handling.
- Idempotency and duplicate protection.
- Prevention of overlapping scheduled executions where relevant.
- Structured logs with secrets and sensitive data redacted.
- Last-known-good aggregate preservation.
- Data-freshness monitoring.
- A documented stop mechanism.
- A named review owner and escalation process.
- Recovery and rollback planning for any approved schema or storage changes.

A failed ingestion must not silently replace valid previous outputs with empty results.

## 11. Phased implementation roadmap

### Phase A — National airport catalogue

- Define the inventory scope.
- Audit the existing 320-record airport master.
- Reconcile identifiers and aliases.
- Document missing facility categories and source gaps.
- Add validation and provenance checks.
- Publish a coverage report with explicit limitations.

**Exit condition:** The airport catalogue has a declared scope, reproducible validation, documented provenance, and a measurable gap report.

### Phase B — Dashboard with approved reference and fixture data

- Build the national overview.
- Build the airport intelligence view.
- Build regional analysis.
- Add data-quality and freshness indicators.
- Test missing, stale, and incomplete data states.
- Ensure no fabricated traffic values appear.

**Exit condition:** The dashboard produces interpretable, source-labelled analysis using approved reference data and clearly identified test fixtures.

### Phase C — Provider compliance and feasibility design

- Complete the provider licence and usage review.
- Obtain the necessary access and usage guidance.
- Finalize the data contract and publication model.
- Define geographic query geometry and request budgets.
- Resolve retention and deletion rules.
- Define entry criteria, stop conditions, monitoring, and responsibilities.

**Exit condition:** All required permissions and design decisions are documented; unresolved conditions remain explicit.

### Phase D — Bounded pilot, only after formal approval

- Verify the effective runtime configuration.
- Test approved credentials and permissions through the authorized workflow.
- Enforce the approved request and payload budgets.
- Monitor coverage, freshness, errors, and quota behavior.
- Compare actual performance with the documented feasibility estimate.
- Stop immediately if a compliance or safety condition is violated.

**Exit condition:** The pilot meets its documented technical, data-quality, operational, and compliance acceptance criteria.

### Phase E — Production decision

- Review pilot evidence.
- Verify cumulative limits and operational controls.
- Complete retention and deletion verification.
- Review approved dashboard outputs.
- Confirm deployment and access controls.
- Record an explicit production decision.

**Exit condition:** Written approval based on evidence—not merely a successful code run.

## 12. Acceptance criteria

The blueprint is ready for pilot consideration only when the applicable items below are evidenced.

### Airport catalogue

- A defined India airport/aerodrome scope exists.
- The current master has been audited against that scope.
- Duplicates and unresolved identity conflicts are reported.
- Source provenance is retained.
- Missing attributes remain explicitly unknown.
- The coverage report is reproducible.

### Dashboard

- Metric definitions and source lineage are documented.
- Airport and regional comparisons use consistent time windows and units.
- Freshness and coverage limitations are visible.
- Missing data is not represented as zero traffic.
- Observed aircraft and inferred movements are clearly distinguished.
- The product has been tested with incomplete, stale, and invalid fixtures.

### ADS-B feasibility

- Provider permission and access conditions are recorded.
- The collection scope and polling interval are approved.
- Query count and payload estimates are documented.
- Required request limits are enforced and tested.
- Retention and deletion rules are approved and verifiable.
- Raw and derived output permissions are resolved.
- Entry criteria, stop conditions, monitoring, and responsibilities are defined.

### Governance

- Every source has an explicit review status.
- Every published output has an approved use.
- Changes to source terms or collection scope trigger reassessment.
- A formal stage-gate decision is recorded.

## 13. Risks and limitations

| Risk | Mitigation |
|---|---|
| Airport inventory is incomplete | Reconcile the master against suitable sources and publish scope limitations |
| ADS-B coverage varies geographically | Report observation coverage and avoid treating missing data as zero activity |
| Broad coverage exceeds provider limits | Estimate query volume before selecting a refresh schedule |
| Timestamp quality is insufficient | Separate observation time from ingestion time and block unsupported freshness claims |
| Provider terms restrict storage or redistribution | Resolve terms before collection and publishing |
| Airport proximity is mistaken for an arrival or departure | Define and validate movement inference separately |
| Metrics change after source or schema updates | Version transformations and monitor schema and quality changes |
| Dashboard looks authoritative despite weak evidence | Make source, freshness, completeness, and confidence limitations visible |
| Destructive retention logic causes data loss | Require dry-run-first behavior, tests, audit records, and recovery planning |

## 14. Current project decision

**Status: Planning only — not approved for live collection.**

The current project records the following safeguards:

- `collection.enabled = false`
- `adsb.enabled = false`
- `adsb.pilot_mode = true`
- Raw-data publication disabled.
- Public API disabled.

The example configuration has passed a dry-run safety check, but effective scheduled and production runtime configurations remain unverified.

The provider compliance review, broad-coverage feasibility, operational request limits, retention enforcement, and final approval remain outstanding.

This blueprint does not authorize API calls, production database changes, deletion jobs, or public release.

**Next decision:** Complete the national airport inventory audit and the provider compliance review before deciding whether a broad-India ADS-B pilot is feasible.
