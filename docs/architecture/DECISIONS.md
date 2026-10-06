# Architecture Decisions — 0.1.0

## Adoption record (T-00)

**2026-10-06 — ADOPTED by team lead (ĐinhTruong An, PM/PO)** as the project's *synthetic* academic policy. These are project rules for synthetic data, not a real university's regulations.

| Item | Adopted value |
|---|---|
| Contract | `0.1.0` (was `0.1.0-proposed`); API path `/v1` |
| Decisions | D-01…D-17 adopted as selected below; D-13 grade scale 0–10, pass `>= 5`; D-08 prerequisites AND, passed in an earlier term only |
| Failed / repeat (D-15) | failed never satisfies prerequisites; a failed course **may be recommended again** (retake) if its own prerequisites are met; latest record wins is out of scope (one record per course in v0.1) |
| Score weights (A-06) | defaults goal .50 / interest .20 / preparation .10 / workload .20; missing components renormalized (A-04) |
| Persistence (D-04) | stateless API, synthetic profiles only; no retention requirement |
| Offerings (D-14) | synthetic catalog declares `available_terms` explicitly |
| RE-094 (771 users, 38 days, 10 h CR) | not adopted |
| ADR-001, FAIRNESS.md | adopted |

The rows below keep the original rationale; "Draft selection" now reads as the adopted selection unless the adoption record says otherwise.


| ID | Problem | Draft selection | Alternatives | Rationale / trade-off | Reconsider when |
|---|---|---|---|---|---|
| D-01 | No backend stack established | Python 3.12+, FastAPI; React + TypeScript | Django; Node/Nest; single static prototype | Typed HTTP boundary, plain Python domain, separate web client; introduces two runtimes | course team/runtime constraint or deployment platform is known |
| D-02 | Need independent domain testing | Modular monolith with ports/adapters | microservices | simpler local setup and atomic deterministic flow; scale/deployment coupled | independent scaling/ownership becomes measured need |
| D-03 | Structured academic rules | deterministic engines; no LLM in core | LLM ranking/explanation; RAG | reproducible eligibility and evidence; less natural open-text goal interpretation | validated unstructured goal need and evaluated safe benefit exist |
| D-04 | Profile persistence unknown | stateless API; request-scoped synthetic profile, local UI draft | PostgreSQL, browser account storage | avoids unsupported retention/security assumptions; no cross-session recovery | product requires account, shared plan or retention policy |
| D-05 | Catalog source unknown | versioned in-memory snapshot adapter | SQL/catalog service | zero unneeded infrastructure; operational refresh is manual | real source, size or update guarantees require it |
| D-06 | Contract for clients | OpenAPI 3.1, `/v1`, JSON | generated RPC / GraphQL | explicit consumer fixtures and conventional tooling; versioning overhead | client needs show query flexibility beyond bounded resources |
| D-07 | Rule semantics uncertain | fixture rules recorded as PROPOSED, do not silently adopt | treat fixture as canonical | preserves academic decision authority; downstream implementation waits | policy owner explicitly accepts a version |
| D-08 | Same-term dependency | only historically passed prerequisite satisfies eligibility | allow concurrent prerequisite | avoids assuming registration semantics; may defer valid combinations | registrar/course policy explicitly supports corequisites/concurrent enrollment |
| D-09 | Explanation language | deterministic templates from evidence | generated text | grounded and reproducible; limited stylistic flexibility | user research shows need and validated paraphrase design exists |
| D-10 | Score display | weighted normalized suitability 0–1, percent UI | rank-only / probability | inspectable contributions; weights/maps still require validation | stakeholders choose different score semantics |
| D-11 | Plan algorithm | deterministic ordered greedy heuristic, non-optimal | optimization solver | transparent and dependency-light; can miss feasible combinations | required optimality/scale is adopted and solver can be verified |
| D-12 | Operations/hosting | no infra dependency specified; local ASGI + static web for prototype stage | containers/cloud/Redis/DB | project has no measured availability/persistence requirement; lacks production ops | actual hosting, load, auth or availability needs are accepted |
| D-13 | Grade semantics | 0–10 and >=5 only as fixture assumption | letter grades / pass-status enum | allows concrete fixture arithmetic but is not institution policy | official grading/repeat/withdrawal rules supplied |
| D-14 | Offerings | use declared terms; unknown stays unavailable/unknown | assume all terms | avoids fabricated roadmap availability; fixture all-term is illustrative only | validated catalog defines offerings |
| D-15 | Failed/repeated course recommendation | Keep failed distinct from passed; do not satisfy prerequisites; retake eligibility unresolved | Treat failed as passed; exclude failed from recommendations | Avoid false eligibility while preserving the unresolved retake choice | Official repeat, grade replacement and enrollment rules supplied |
| D-16 | Rules vs ML recommender (required ADR) | deterministic rules + weighted scoring with hard prerequisite gate; see `adr/ADR-001-rules-vs-ml.md` | content-based, collaborative filtering, learning-to-rank, hybrid | no real interaction data; explanation and what-if must be exact and testable | permitted real interaction data exists; ADR-001 evidence (T-14) shows ML benefit |
| D-17 | Fairness verification | group labels only in synthetic sidecar `cohorts.json`; counterfactual invariance + exposure/coverage report; see `FAIRNESS.md` | no fairness checks; group attributes inside profile | API schema forbids extra profile fields, so ranking cannot read group labels | real data or learned components are introduced |

## Explicit fixture policy disposition

| Fixture proposal | Disposition | Reason / acceptance evidence |
|---|---|---|
| grade scale 0–10 | MODIFY: retain as example only | no registrar policy; not accepted |
| passing grade 5 | MODIFY: retain as example only | material academic rule; not accepted |
| mandatory prerequisite AND | ACCEPT as draft architecture invariant, pending human review | common-context explicitly requires initial AND; this is instruction, not academic acceptance |
| prerequisites passed before semester | ACCEPT as draft architecture invariant, pending human review | common-context hard invariant; no same-term satisfaction |
| workload in hours/week | ACCEPT as proposed unit | fixture and product scope specify workload preference; no measured estimates or acceptance |
| offerings all terms | REJECT as general policy; fixture-only | catalog must declare terms; unknown availability cannot be assumed |
| BASE/FAILED/READY outcomes | ACCEPT as fixture consistency oracle only | checked against proposed data, not real policy |
| .86/.58 and .44/.82 | ACCEPT as component arithmetic oracle only | independently hand-calculated; not goal extraction or approved weights |
| ranking components/weights | PROPOSE | no product acceptance or validated mapping |
| 771 concurrent, 38-day retention, 10-hour CR (RE-094) | REJECT as shared requirement for now | brainstorm explicitly says individual variant, group confirmation needed |
| profile/plan persistence | PROPOSE stateless v0.1 | retention and multi-device needs unknown |

## Assumption register

| ID | Assumption | Status | Evidence / acceptance |
|---|---|---|---|
| A-01 | Synthetic profiles only in initial build | PROPOSED | brainstorm; no real student data authorized |
| A-02 | Courses have stable IDs and integer credits | PROPOSED | fixture shape; catalog owner must validate |
| A-03 | In-memory versioned catalog suffices for prototype | PROPOSED | no backend/source currently exists |
| A-04 | Missing workload means missing component, renormalize remaining weights | PROPOSED | algorithm draft; product review needed |
| A-05 | Greedy planning is acceptable without optimality | PROPOSED | no optimization requirement or plan policy accepted |
| A-06 | Defaults .50/.20/.10/.20 | PROPOSED | design placeholder; user-facing defaults require acceptance |
| A-07 | Response p95 <500ms at concurrency 50 | PROPOSED target | no runtime measurement or deployment evidence |

