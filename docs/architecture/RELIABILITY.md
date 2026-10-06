# Reliability and Verification — Proposed

No runtime SLA, deployment topology or telemetry backend has been accepted. Targets in this document are proposals, not measurements. Keep logs synthetic and redact profile payloads.

## Failure policy

| Failure | Observable behavior | Safe continuation |
|---|---|---|
| Invalid catalog reference/cycle/duplicate ID | Reject snapshot; return 409/503 with request ID and catalog version | No eligibility, score, plan or personalized fallback |
| Catalog source unavailable | Use only validated, versioned snapshot if explicitly configured; mark degraded, show source and age | Otherwise 503; do not use stale unknown data |
| Ranking failure | Preserve independently computed eligibility only if DTO marks ranking unavailable/degraded; otherwise 503 | Never invent rank/score |
| Explanation failure/evidence mismatch | Omit unverified reason; warning with code; scores remain only if valid | No unsupported prose |
| Empty eligible set | 200 `empty`, empty eligible list, relevant ineligible/why-not reasons | Normal outcome, not service failure |
| Invalid what-if input | 422 with field errors; discard scenario overlay | Baseline object and prior response remain immutable |
| Infeasible semester plan | 200 `infeasible` or `partial`, every unscheduled item with a reason | No silent selected-course removal |
| Infeasible roadmap | 200 partial/infeasible and blockers (missing prerequisite, unknown offering, horizon, credit cap) | No invalid ordering and no optimality claim |
| Stale catalog / baseline | 409 with current versions if safe to disclose | Caller refreshes and recomputes |
| Unexpected internal error | 500 generic safe body + request ID; internal diagnostic excludes profile content | No stack trace or sensitive data to client |

## Quality scenarios

| ID / source | Stimulus and environment | Required response | Proposed measurable target | Verification method / status |
|---|---|---|---|---|
| Q-01 Student | BASE profile, valid catalog, request recommendation | ST201 and SE201 eligible; AI301 direct missing ST201; DL401 direct missing AI301 | 100% expected eligibility agreement on fixture set | Domain assertions; UNRUN |
| Q-02 Catalog owner | inject dangling ref and cycle | invalid snapshot, no claims of eligibility | detect 100% of injected corruptions | graph tests; UNRUN |
| Q-03 Student | compare career vs light weights | contributions sum and order reverses for ST201/SE201 | abs(sum contributions-total) <= 1e-9; repeat output byte-stable excluding request IDs | independent arithmetic + repeat test; UNRUN |
| Q-04 Student | simulate hypothetical pass/weight changes | new scenario ID, unchanged baseline digest, deltas only comparable candidates | 0 baseline field changes | immutability assertion; UNRUN |
| Q-05 Student | plan 3-credit cap with two 3-credit courses and a blocked course | no over-cap/ineligible inclusion; precise excluded reasons | 100% returned complete plans satisfy limits | domain boundary tests; UNRUN |
| Q-06 Student | roadmap AI301 then DL401 | dependent appears only in later term after prerequisite completion | 0 same-term prerequisite violations | roadmap graph assertion; UNRUN |
| Q-07 Partner | catalog outage injection | 503, request ID, retryability; no personalized fallback | 100% injected outages safe | API fault-injection test; UNRUN |
| Q-08 Student | empty eligibility | stable 200 empty result and why-not access | 100% schema-valid empty responses | contract test; UNRUN |
| Q-09 Student | corrupt explanation evidence reference | omit unsupported explanation and degrade | 0 ungrounded explanation refs | evidence referential-integrity assertion; UNRUN |
| Q-10 API consumer | 50 concurrent local requests | deterministic stateless outputs | proposed p95 <500ms | future load test; UNRUN; no deployment environment |
| Q-11 Researcher | usability sessions | participants correctly restate reason and prerequisite | brainstorm proposal >=80% among 5–8 users | future consented synthetic-profile study; UNRUN |

No target is represented as achieved. RE-094 throughput/retention/change-response values are not adopted. Observability proposal: structured event fields `request_id`, operation, contract/catalog/algorithm versions, status, duration and error code; avoid logging profile/history/goals. Add OpenTelemetry only when deployment and operational owner are known; no telemetry dependency in prototype architecture.

## Verification checklist

- Eligibility: passed-only AND prerequisite semantics, completed exclusion, failed/planned/hypothetical separation, direct and transitive blockers.
- Ranking: finite normalized weights, all-zero rejection, missing-component behavior, reproducible tie-break, contribution reconciliation, arithmetic oracle.
- Explanations: every reason code has evidence refs; no invented prerequisite or career claim; conditional unlock accounts for every remaining prerequisite.
- What-if: baseline deep equality, scenario version, comparable candidate set, entrants/exits distinct from rank changes.
- Planning: no duplicates, completion or ineligible course; credits never exceed cap; partial/infeasible reasons complete.
- Roadmap: prerequisite term earlier than dependent, offering declared, horizon bounded, no optimality promise.
- Contract: every fixture parses, valid requests satisfy schemas, invalid ones fail, response fixtures match declared response schemas, OpenAPI refs resolve.
- Integration: same fixture passes backend DTO and web adapter; mock status remains explicit until live service test.

Checks not run during design: application tests (no implementation), browser/device QA, load/latency, usability, live integration, security/deployment review and independent architecture review.
