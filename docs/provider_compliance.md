# Provider Compliance and Data Use Review

**Status:** In progress  

**Last reviewed:** 2026-10-23  

**Scope:** Data-source licensing, permitted use, retention, attribution, redistribution, and publication controls.

## 1. Purpose

This document tracks provider-specific compliance reviews for India Flight Intelligence.

Recording a licence name or public API endpoint does not, by itself, establish permission for every intended use. Live collection and public release must remain disabled until the applicable terms, access requirements, and usage limits have been reviewed and the required approvals have been documented.

## 2. Current ADS-B provider review

### adsb.lol

- **Provider:** adsb.lol

- **Website:** https://adsb.lol/

- **API base URL:** https://api.adsb.lol

- **Documented API route:** `/v2/lat/{lat}/lon/{lon}/dist/{radius}`

- **Recorded licence:** ODbL 1.0 (provider-stated)

- **Review status:** Under review

- **Live collection:** Not approved

- **Public release:** Not approved

### Recorded evidence

The source licence register records that the provider states the API and public data use ODbL 1.0. It also records that older API documentation is deprecated, API v2 documents the geographic search route above, rate limits are dynamic, and production users should discuss their usage with the provider.

The register further records that API-key requests require an ODbL compliance explanation.

Reference links:

- https://www.adsb.lol/about

- https://api.adsb.lol/docs

- https://www.adsb.lol/request

These links are evidence for review, not proof that this project has been granted access or that every intended use is permitted.

## 3. Outstanding review items

Before live ADS-B collection or public release is considered, document the outcome of each item below.

- [ ] Review the applicable ODbL 1.0 obligations for the intended use.

- [ ] Determine attribution requirements and where attribution must appear.

- [ ] Assess share-alike obligations and whether any produced database would be covered.

- [ ] Assess database rights and obligations associated with extracted or reused data.

- [ ] Determine whether derived databases, aggregates, visualizations, and downloadable outputs have different obligations.

- [ ] Confirm whether raw observations may be stored and for how long.

- [ ] Confirm whether transformed observations and aggregate outputs may be retained and redistributed.

- [ ] Contact the provider to discuss intended production usage and applicable rate limits.

- [ ] Document any access or API-key requirements and the provider's response.

- [ ] Review the final proposed use and publication model before enabling collection.

Unknown or unresolved items must remain marked as such. Do not infer approval from successful technical requests or passing automated tests.

## 4. Intended project use to be reviewed

India Flight Intelligence is intended to support aviation analytics and dashboards. The proposed data flow may include:

1. Retrieving observations from an external provider.

2. Validating and transforming observations.

3. Calculating analytical metrics and aggregates.

4. Retaining data according to documented policies.

5. Displaying approved metrics in dashboards or reports.

The permitted scope of each step must be checked against the applicable provider terms. This description records the intended workflow; it does not assert that the provider has approved it.

Before requesting access, document the actual proposed polling frequency, geographic coverage, fields collected, expected request volume, storage design, retention periods, derived-data methodology, attribution, and public outputs.

## 5. Technical safeguards

Until the provider review is complete:

- Keep `collection.enabled` set to `false`.

- Keep `adsb.enabled` set to `false`.

- Keep `adsb.pilot_mode` set to `true`.

- Keep raw-data publication disabled.

- Do not make live ADS-B API requests as part of validation or testing.

- Use mocked responses and local fixtures for automated tests.

- Do not treat endpoint validation, a successful test run, or a successful GitHub push as licensing or access approval.

- Do not publish raw observations or derived outputs whose redistribution status remains unresolved.

Configuration values in `config/settings.example.json` are example settings. Verify the effective runtime configuration separately before any future operational change.

## 6. Retention and deletion

The tier-based live ADS-B retention targets are recorded in `docs/retention_policy.md`. Those targets are project design decisions and are not, by themselves, evidence that the provider permits the proposed retention periods.

Before collection is enabled, assess those targets against the applicable provider terms. Record any necessary changes and the basis for them.

Any future deletion implementation must retain the documented dry-run-first behavior, tests, audit records, and recovery planning.

## 7. Approval and change control

A provider review is complete only when the evidence, decisions, unresolved conditions, and responsible approval are recorded.

For each reviewed source, retain:

- Applicable terms and the date reviewed.

- Relevant provider correspondence or access conditions.

- Attribution and redistribution decisions.

- Approved request limits and collection scope.

- Approved retention and deletion rules.

- Permitted aggregate and publication uses.

- Review status and the date of the decision.

Any material change to the provider terms, API, collection frequency, stored fields, retention, or publication scope requires reassessment.

## 8. Current decision

**adsb.lol remains under review. Live collection and public release remain blocked.**

No approval is implied by this document. Update `config/source_licences.csv` only when new evidence supports a change in status. Keep unresolved fields marked as unknown until verified.

Other sources, including AAI, DGCA, Aviation Weather Center, Iowa Mesonet, and OurAirports, must be assessed according to their respective terms and the intended use of their data.


