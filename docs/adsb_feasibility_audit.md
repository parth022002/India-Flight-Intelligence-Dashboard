# ADS-B Feasibility and Technical Safety Audit

**Status:** In progress — not approved for live collection
**Review date:** 2026-10-23
**Scope:** ADS-B client safeguards, configuration limits, test evidence, provider compliance, and Stage 4 readiness.

## 1. Purpose

This document records the evidence available for evaluating the technical feasibility and operational readiness of the India Flight Intelligence ADS-B collector.

Passing tests demonstrates tested software behavior. It does not establish provider permission, production access, acceptable provider load, or permission to retain and redistribute data.

**Current decision:** Keep live ADS-B collection disabled and public release blocked until the outstanding provider and operational reviews are resolved.

## 2. Technical implementation reviewed

The following project components were inspected:

- `src/flight_intelligence/collectors/adsb_client.py`
- `src/flight_intelligence/collectors/adsb_orchestrator.py`
- `src/flight_intelligence/config.py`
- `scripts/collect_adsb.py`
- `tests/unit/test_adsb_client.py`
- `tests/unit/test_config.py`
- `tests/unit/test_adsb_runner.py`
- `docs/provider_compliance.md`
- `docs/operational_runbook.md`
- `docs/stage_plan.md`
- `config/settings.example.json`

### Verified safeguards

- The ADS-B client requires its enablement configuration to be true.
- Client enablement requires `collection.enabled`, `adsb.enabled`, and `adsb.pilot_mode` all to be true.
- The client validates the ADS-B API v2 geographic endpoint format and its coordinate and radius values.
- HTTP requests use bounded timeouts and retry behavior.
- Request attempts and cumulative response payload bytes are bounded within an `AdsbClient` instance.
- The runner's dry-run path does not connect to the database or make HTTP requests.
- The runner requires an explicit database URL environment-variable name and does not automatically register or approve sources.
- The orchestrator checks that the selected source exists, has the expected ADS-B data type and provider name, and has an approved source status before making a request.
- Failure handling avoids logging raw exception text that may contain sensitive details.
- Raw payload persistence requires an explicit command-line option.

These are code-review findings. They do not establish that live collection is authorized or operationally feasible.

## 3. Configuration limits

The example configuration currently records:

| Setting | Configured value |
|---|---:|
| `collection.enabled` | `false` |
| `adsb.enabled` | `false` |
| `adsb.pilot_mode` | `true` |
| `adsb.max_requests_per_run` | 2 |
| `adsb.max_payload_mb_per_run` | 5 MB |
| `limits.max_requests_per_run` | 10 |
| `limits.max_payload_mb_per_run` | 25 MB |
| `adsb.request_timeout_seconds` | 20 |
| `adsb.max_retries` | 2 |
| `adsb.retry_backoff_seconds` | 2 |
| `adsb.publish_raw_data` | `false` |
| `collection.publish_raw_data` | `false` |

These values are example settings, not proof of the effective runtime configuration.

The configuration loader checks that the ADS-B request and payload budgets do not exceed the application-wide configured ceilings. The runner constructs one client per invocation, and the orchestrator makes one collection call through that client.

**Limit scope decision (documented interpretation):** For the current single-runner workflow, `adsb.max_requests_per_run` and `adsb.max_payload_mb_per_run` are intended to bound HTTP attempts (including retries) and response bytes, respectively, within one runner invocation. The `limits.max_requests_per_run` and `limits.max_payload_mb_per_run` settings act as configuration ceilings against which the ADS-B-specific budgets are validated; they are not shared cumulative runtime counters across separate invocations or client instances.

This interpretation matches the current implementation. It does not provide a global rate or quota limit across concurrent processes, repeated invocations, or a time window. If those protections are required for a future scheduled or concurrent deployment, they must be designed and tested separately. This documented interpretation does not authorize live collection.

## 4. Automated validation evidence

The following results were observed during local validation:

| Validation | Result |
|---|---|
| ADS-B client unit tests | 40 passed |
| ADS-B runner unit tests | 4 passed |
| Configuration tests after enablement-gate coverage was added | 38 passed |
| Full unit suite after the new tests | 176 passed |
| Earlier full test suite, including integration tests | 181 passed |
| Ruff check for the modified configuration test file | Passed |
| Git diff whitespace check | Passed |

The configuration tests now explicitly cover the four combinations in which each of the three enablement switches independently blocks the client and all three together enable it.

These results are evidence of tested behavior at the time of execution. They do not establish provider approval, actual provider rate limits, production readiness, or effective runtime configuration.

## 5. Provider compliance and access

The existing `docs/provider_compliance.md` records adsb.lol as under review, with live collection and public release not approved.

The project still needs documented evidence covering:

- Applicable ODbL 1.0 obligations for the intended use.
- Attribution requirements and placement.
- Share-alike and database-rights implications.
- Treatment of derived databases, aggregates, visualizations, and downloadable outputs.
- Permitted retention of raw and transformed observations.
- Provider-confirmed usage limits and intended production request volume.
- API-key, access, or other provider requirements.
- Approval of the final collection, storage, retention, and publication model.

The provider's published materials and API documentation are review references; they are not evidence that this project has been granted production access or permission for every intended use.

No provider approval is inferred from code tests, successful commits, or endpoint validation.

## 6. Feasibility assessment

### Technically supported

The project has an ADS-B client, configuration validation, a guarded single-run collection path, source-approval checks, retry and payload limits, and automated tests.

### Not yet established

The following remain unresolved:

1. Provider permission and applicable licensing obligations.
2. Provider-approved request rates, quotas, and access requirements.
3. Whether the proposed collection scope and data availability support the intended analytics.
4. Whether retention and redistribution plans are permitted.
5. Whether application-wide limits are enforced across repeated executions.
6. Whether the effective runtime configuration matches the safe example settings.
7. Whether a bounded pilot can be authorized and executed under documented conditions.

Because live collection is not approved, empirical feasibility based on live provider responses has not been established.

## 7. Required actions before a pilot

- [ ] Complete the provider licensing and access review.
- [ ] Document proposed geographic coverage, collection frequency, fields, expected request volume, storage, retention, and outputs.
- [ ] Obtain and record provider guidance or approval for the intended usage and applicable limits.
- [ ] Decide whether application-wide limits apply per client, per process, per scheduled run, or across a wider period.
- [ ] Add and test cumulative enforcement if the agreed design requires it.
- [x] Verify the example configuration without enabling collection: the dry run confirmed collection and ADS-B are disabled, pilot mode is enabled, raw payload persistence is disabled, and no database or network request was made. No separate local settings file exists; scheduled and production runtime configurations remain unverified.
- [ ] Review retention, deletion, attribution, and redistribution controls against the approved use.
- [ ] Define explicit pilot entry criteria, stop conditions, logging, and review responsibilities.
- [ ] Record a formal decision before any live request is authorized.

## 8. Current decision

**Stage 4 remains in progress.**

Technical safeguards and test coverage have been implemented and reviewed, but the provider compliance review, approved operational limits, effective-runtime verification, and feasibility sign-off remain outstanding.

Until those requirements are resolved, keep `collection.enabled` and `adsb.enabled` set to `false`, retain the current pilot-mode setting, do not make live ADS-B requests, and do not publish raw observations or unapproved derived outputs.

The next stage-gate decision must be based on recorded evidence and explicit approval, not on the existence of this document alone.
