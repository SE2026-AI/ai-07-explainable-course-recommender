# API Contract — `/v1` (0.1.0, adopted 2026-10-06)

This document describes the stateless contract in `contracts/openapi.yaml`. No endpoint is implemented yet. Profile-bearing operations are repeatable requests; the caller sends profile state explicitly. `profile_id` is a synthetic identifier, not authentication. No PII or real student records are permitted in fixtures.

## Resource map

| Operation | Producer | Consumers | Purpose / status |
|---|---|---|---|
| `GET /catalog/courses` | Catalog adapter + API | Web, partner clients | Versioned, filterable catalog page |
| `GET /catalog/graph` | Prerequisite engine + API | Graph UI, roadmap | Prerequisite→dependent edges |
| `POST /profiles/validate` | Profile validator | Web, partner clients | Validate without storing profile |
| `POST /recommendations` | Recommendation use case | Web, mobile/partner | Eligible ranked and relevant ineligible sets |
| `POST /why-not` | Eligibility/explanation | Web, partner clients | Explain specified course IDs, including completed |
| `POST /simulations` | Simulation use case | Web | Immutable baseline vs overlay scenario |
| `POST /semester-plans` | Term planner | Web | Selected course disposition under term and credit cap |
| `POST /roadmaps` | Roadmap planner | Web | Bounded deterministic multi-term plan |

Request and response schemas are in OpenAPI. Every body-bearing operation has a valid and invalid request fixture named `{operation}-valid.json` / `{operation}-invalid.json`. GET query parameters are validated by OpenAPI; invalid catalog version returns 409 and limit outside 1–100 returns 422. Response fixtures cover recommendation success/empty, blocked why-not, simulation comparison, complete/infeasible plan, complete/partial roadmap and catalog outage. Fixtures show proposed contract examples, not observed server output.

## Cross-cutting contract

- API version is path `/v1`; `contract_version` in body is `0.1.0`. Reject unsupported contract/catalog versions; never silently reinterpret.
- Echo caller `request_id` or generate one. It is a correlation ID, not an idempotency key.
- `catalog_version` and `algorithm_version` make scores reproducible. Responses that rank also identify candidate cohort/comparison set.
- Course identifiers are stable IDs, not titles; term IDs are catalog-defined strings. Credits are integer credit units; workload values are hours/week.
- Hard mandatory prerequisites gate eligibility; recommended preparation is a soft score signal. Missing references/cycles invalidate catalog.
- Score totals are suitability only. Component values and contributions reconcile; ranking comparison uses the same version, algorithm, eligibility cohort and candidate-set digest.
- Scenario always names `baseline_version`, `scenario_id`, and `scenario_version`. Scenario results never replace baseline.
- Plan `complete` means all requested constraints met; `partial` means some requested items are placed and others have reasoned exclusions; `infeasible` means no requested course could be placed or explicit constraints cannot be met. Every unplaced item has a reason. Roadmap prerequisite completion must occur before dependent term.

## Status and errors

| HTTP | Meaning |
|---:|---|
| 200 | Successful operation; `status` may be `ok`, `empty`, `degraded`, `complete`, `partial` or `infeasible` as defined by operation |
| 400 | Malformed JSON |
| 404 | Unknown resource/course lookup path; why-not for an unknown course uses 422 validation unless a later contract explicitly changes it |
| 409 | Unknown/stale catalog version, invalid graph or incompatible baseline version |
| 422 | Invalid fields, policy constraints, unknown course IDs or invalid scenario |
| 503 | Required catalog/engine unavailable with no verifiable safe result |

Error object is `{request_id, contract_version, error:{code,message,retryable,details?}}`. Do not put sensitive values in `details`. A degraded response is allowed only when returned eligibility and fields remain independently verifiable; omitted sections are named in warnings. Catalog outage cannot return personalized ranking. Ranking failure may return independently computed eligibility only if response schema clearly marks no ranking and status degraded; otherwise use 503.

## Example mapping

| Operation / branch | Fixture |
|---|---|
| Catalog list and graph query valid/invalid | `catalog-courses-valid.json`, `catalog-courses-invalid.json`, `graph-valid.json`, `graph-invalid.json` |
| Profile validation valid/invalid | `profile-valid.json`, `profile-invalid.json` |
| Recommendation request valid/invalid | `recommendation-valid.json`, `recommendation-invalid.json` |
| Recommendation success/empty | `recommendation-success.json`, `recommendation-empty.json` |
| Why-not request valid/invalid and blocked result | `why-not-valid.json`, `why-not-invalid.json`, `why-not-blocked.json` |
| Simulation request valid/invalid and compare | `simulation-valid.json`, `simulation-invalid.json`, `simulation-comparison.json` |
| Semester-plan request valid/invalid and outcomes | `semester-plan-valid.json`, `semester-plan-invalid.json`, `semester-plan-complete.json`, `semester-plan-infeasible.json` |
| Roadmap request valid/invalid and outcomes | `roadmap-valid.json`, `roadmap-invalid.json`, `roadmap-complete.json`, `roadmap-partial.json` |
| Unavailable catalog | `catalog-unavailable.json` |

## Implementation notes

Transport maps validation and domain errors to the status table. Application use cases take explicit `CatalogSnapshot` and `StudentProfile`; no service reads HTTP context. Recommendation response retains separate eligible and ineligible arrays. Unknown/missing grade cannot satisfy prerequisites. Recommended preparation cannot block. Credit selection does not change academic history. See `DATA_MODEL.md`, `RECOMMENDER_DESIGN.md`, and `RELIABILITY.md` for domain behavior and open policy choices.
