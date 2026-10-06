# Architecture Handoff — AI-07

## Status

> **Update 2026-10-06:** Material decisions 1–6 below were adopted by the team lead as synthetic project policy (T-00, see `docs/architecture/DECISIONS.md`). Contract is now `0.1.0`. Ticket owners are tracked in `BACKLOG.md`.

**PARTIAL** — draft architecture and contract 0.1.0-proposed prepared; pending consistency validation and human adoption of material domain rules. Review status: **INDEPENDENT_REVIEW_PENDING**. Integration: **MOCK_ONLY**. This is not a self-approved architecture gate.

## Assignment preflight

- Task: architecture prompt `docs/tasks/prompts/01-architecture.md`, including mandatory v2 control packet; project requirement IDs are not assigned in repository, so trace by named invariants in prompt.
- Inputs: common context v2; protocol v1.0; assignment template; prompt README; fixtures `prompt-fixture-v2-proposed`; brainstorm; README; architecture README; RELATED_WORK.md; pipeline; `src/prototype/index.html`; aicb-agentic-engineer skill.
- Workspace: `truongan_22001535`; input HEAD/diff not pinned because checkout includes pre-existing user changes. Existing RELATED_WORK.md diff was recorded before edits and left untouched.
- Accepted contract: none. Proposed version: `0.1.0-proposed`.
- Allowed writes: `docs/architecture/**`, `docs/tasks/ARCHITECTURE_HANDOFF.md`. No app, test, prompt, pipeline, manifest or git history changes.
- Baseline: one existing modified file `docs/architecture/RELATED_WORK.md`; architecture README existed; no canonical backend contracts or framework manifests found.

## Outputs

- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/DATA_MODEL.md`
- `docs/architecture/RECOMMENDER_DESIGN.md`
- `docs/architecture/API.md`
- `docs/architecture/RELIABILITY.md`
- `docs/architecture/DECISIONS.md`
- `docs/architecture/contracts/openapi.yaml`
- `docs/architecture/contracts/examples/*.json`
- This handoff

Stack proposal: FastAPI + Python modular monolith and React/TypeScript client. Domain is deterministic; no persistence/infrastructure requirement accepted. Stateless profile-bearing operations allow mock-first web work. The prototype is browser-only with mock catalog/profile/scoring/API and local plan state; it is not an API implementation.

## Material decisions needed

1. Passing/grade/missing-grade/repeat policy; fixture proposes 0–10 and >=5. Option: adopt as synthetic project policy, or supply institution-specific scale and repeat/withdrawal handling.
2. Confirm mandatory prerequisite AND and passed-before-term semantics, including exceptions/corequisites. Common context instructs initial AND and no same-semester satisfaction; academic owner still reviews application.
3. Confirm units and data ownership: credits, workload hours/week, course IDs, goals/skills mapping and offering calendar.
4. Adopt/modify component set, missing data normalization, defaults and weight constraints. `.86/.58` and `.44/.82` are accepted only as arithmetic oracle; real goal-to-component extraction remains undefined.
5. Confirm whether profile/plan persistence, auth, retention, deployment and performance targets are required. RE-094 figures remain excluded.
6. Confirm planning policy: user selections vs automatic ranking, partial plans, offerings, horizon, repeat constraints and heuristic acceptance.
7. Assign actual writers for shared domain model, app entrypoint, router modules, manifests and canonical contract. No colleague identity is fabricated here.

Unaffected work that can proceed after fixture/interface review: implement a fixture-backed web shell as MOCK_DEPENDENCY; build isolated prerequisite and ranking domain prototypes behind proposed interfaces. Do not lock academic constants or call these integration-complete before acceptance.

## Source interfaces and ownership proposal

| Interface/file | Producer | Consumers | Writer assignment |
|---|---|---|---|
| `CatalogSnapshot`, `Course`, `StudentProfile` | data/catalog domain | prerequisite, rank, plans, API | one catalog/model owner to be assigned |
| prerequisite service | prerequisite domain | recommender, explanation, plan, roadmap, graph | prerequisite feature owner to be assigned |
| ranking/explanation services | ranking domain | recommendation, simulation, UI | ranking feature owner to be assigned |
| simulation/planner services | planning domain | API, web | planning feature owner to be assigned |
| FastAPI entrypoint/router modules | API integration | web and partner clients | one app writer; one writer per router group to be assigned |
| OpenAPI + examples | architecture/API owner | backend serializers, web adapter, contract checker | one canonical contract writer; change proposal required |
| `pyproject.toml` / web manifest | build owner | all code | one manifest owner to be assigned |

Error behaviors are detailed per interface in ARCHITECTURE.md. Domain services remain independent of HTTP.

## Change map

All authored files are new except pre-existing architecture README and user-modified RELATED_WORK.md (untouched). Exact symbol anchors are section headings because these are design documents, not source symbols:

| Requirement | Path / anchor | Before → after | Consumer impact |
|---|---|---|---|
| modular boundaries + gate | `docs/architecture/ARCHITECTURE.md` “Product and architecture”, “Gate checklist” | no canonical design → proposed stack, interfaces, status gates | all future implementation owners |
| domain/policy | `docs/architecture/DATA_MODEL.md` “Profile and state”, “Eligibility…” | no shared model → proposed versioned entities/states | catalog, prerequisite, ranking, planning |
| score/explanation | `docs/architecture/RECOMMENDER_DESIGN.md` “Components…” | prototype-only mock score → component oracle and deterministic proposal | ranker, explanation, UI |
| API | `docs/architecture/contracts/openapi.yaml` paths and schemas | no API contract → proposed `/v1` schema | backend/API, web fixture adapter |
| API guidance | `docs/architecture/API.md` “Resource map”, “Status and errors” | none → resource meanings and behavior | partner/web clients |
| decisions | `docs/architecture/DECISIONS.md` “Explicit fixture policy disposition” | fixture ambiguity → explicit proposal/modify/reject list | human policy review |
| reliability | `docs/architecture/RELIABILITY.md` “Failure policy”, “Quality scenarios” | no verified service boundaries → failure and verification proposals | feature owners, reviewer |

## Acceptance evidence matrix

| Outcome | Criterion | Evidence | Status |
|---|---|---|---|
| Architecture draft | required docs and diagrams present | architecture files listed above | PASS for artifact presence after final inspection |
| Fixture semantics | BASE/FAILED/READY and arithmetic coherent | BASE eligibles ST201/SE201; FAILED ST201 blocked by failed MA101 (other courses may remain eligible); READY AI301 eligible/DL401 blocked; score oracle hand-calculated | PASS as fixture-only oracle |
| Requests | valid and invalid request per operation | 12 body request fixtures (six valid/invalid pairs) checked against JSON Schema; four catalog/graph query fixtures checked against declared constraints | PASS |
| OpenAPI consistency | YAML parses, internal refs resolve, invalid requests rejected, response fixtures validate | PyYAML + jsonschema inline check; 12 body request cases, 4 query cases, 9 response cases, 54 internal refs; `openapi-spec-validator` unavailable | PASS for checked scope |
| Domain decisions | human adopts semantics | Adopted by team lead 2026-10-06, see DECISIONS.md "Adoption record (T-00)" | PASS |
| Independent review | reviewer inspects exact files | no independent reviewer assigned | UNVERIFIED |
| Runtime/integration | implementation and consumers run | no app/backend yet | NOT_APPLICABLE to design; MOCK_ONLY |

## Next-agent acceptance checklist

- [ ] Human or product owner resolves material questions and records adopted decision/version; do not treat prompt fixture as approval.
- [ ] Architecture reviewer reports actionable findings independently; architecture gate checklist updated item by item.
- [ ] Contract owner resolves schemas/examples, including cross-field constraints not expressible in JSON Schema (positive weight sum, unique profile history state, catalog reference checks).
- [ ] Domain owners accept interface/error semantics and their exact shared-file ownership.
- [ ] Contract checker validates all JSON and OpenAPI refs; each invalid request is rejected for intended reason.
- [ ] Backend producer maps all domain errors/statuses; web client can use fixtures and clearly labels mock mode.
- [ ] Integration rechecks eligibility, score reconciliation, immutable what-if and plan/roadmap constraints against live implementation.

## Checks and limits

Available at preflight: Python 3.13, PyYAML and `jsonschema` imports succeeded; Node available. No project manifests/runtime were present. Checks run: PyYAML parse, internal `$ref` resolution, all example JSON parsing, 12 body request validity cases, 4 query constraint cases, 9 response schema cases, BASE/FAILED/READY fixture oracle and both weight arithmetic settings. `openapi-spec-validator` package is unavailable, so full OpenAPI semantic validation remains UNVERIFIED. No tests, app implementation, browser verification, performance measurements, independent review or human policy adoption occurred. RELATED_WORK.md cited vendor/research depth limits; marketing claims and abstracts inform questions, not architecture requirements.

## Prompt and output excerpt evidence

Exact task prompt used: repository file `docs/tasks/prompts/01-architecture.md` as inspected on 2026-10-04; it requires outputs under `docs/architecture/` and this handoff. Shared control: `docs/tasks/prompts/common-context.md` v2 and `agent-execution-review-protocol.md` v1.0. No additional agent was delegated. SHA-256: prompt `566C41FFA30A9E3F934132C0BB663DE70BC7B52AA679F221C6A7056D18A79133`; common context `8538BB188E5EBF9D60619AF6A63FD5794E77F48967B68EBAA9F57364F7E7D9E4`; reference fixture `95B23F872F1E1A2D0EFEA8EC44C95DBFF73FA417B462C96062A9FE05B0846977`; pre-existing RELATED_WORK content `A625CE0AAFBA00E61BF538C05459C95EFFE6C8D3ECD33B6BA5CED0C04808B721`.

Meaningful design output excerpt (not human acceptance): “Use a Python 3.12+ / FastAPI modular monolith, with a typed React + TypeScript web client.” Policy treatment: “grade scale 0–10” and “passing grade 5” retained as fixture examples only; all-term offerings rejected as a general assumption; score pairs retained as component-level arithmetic oracle only. Input HEAD: `f9b8c9dfb4491181ee39e17a1dd4733c47b0bb9f`; `RELATED_WORK.md` was pre-modified and preserved (tracked diff existed at preflight). The created documents are the output record; source prompt remains unmodified.
