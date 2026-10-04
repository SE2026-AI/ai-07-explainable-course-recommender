# Prompt Pack v2 — AI-07

Project SE2026-T24 / SE.2026.14. Human requester: PM/PO and primary developer. Do not infer team leadership. These are task specifications, not records of executed agents.

## Start and input packet
1. Read [common context and controls](common-context.md).
2. Read the [shared execution/review protocol](agent-execution-review-protocol.md) for task order, change locations, testing, debugging and evidence.
3. Fill [assignment envelope](assignment-template.md), including exact write files, dependency status and accepted contract version.
4. Send one task prompt with the full shared context/envelope. Separate agents do not inherit chat memory automatically.
5. Include the [reference scenarios](fixtures/reference-scenarios.json) as illustrative proposed data, then identify accepted differences. Do not silently adopt proposed grade, score or offering policies.
6. Save actual runs, output snippets and checks under docs/tasks/runs/ when executed. No fabricated measurements or human corrections.

The independent [visual pipeline](../PIPELINE_TEAM.html) explains runtime branches, parallel development and feedback without human task allocation.

## Coordination and design
- [00 Orchestrator](00-orchestrator.md): dependency-aware delegation and incremental integration.
- [01 Architecture](01-architecture.md): canonical decisions, models, APIs and fixtures.
- [Product/backlog](management/01-product-backlog.md): outcomes, stories and acceptance.
- [Task dispatch](management/02-task-dispatch.md): bounded packets and file ownership.
- [Review/change](management/03-review-change.md): evidence-based findings and scope impact.

## Feature prompts
| Prompt | Required upstream input |
|---|---|
| [Catalog](features/01-catalog.md) | Accepted Course schema and units |
| [Profile/goals](features/02-profile-goals.md) | Catalog IDs and passed/failed policy |
| [Prerequisites](features/03-prerequisites.md) | Validated catalog/profile interfaces |
| [Ranking](features/04-ranking.md) | Eligibility and canonical component definitions |
| [Explanations](features/05-explanations.md) | Actual score/path evidence |
| [What-if](features/06-what-if.md) | Canonical engine and immutable baseline schema |
| [Semester plan](features/07-semester-plan.md) | Eligible ranking, credit and selection policy |
| [Roadmap](features/08-roadmap.md) | Graph/planning, offerings, bounded horizon |
| [Graph UI](features/09-graph-ui.md) | Graph API fixtures and existing web shell |
| [Web](features/10-web.md) | OpenAPI fixtures; live endpoints for integration |
| [API integration](features/11-api-integration.md) | Accepted transport/domain interfaces |
| [Reliability](features/12-reliability.md) | Implemented boundaries and adopted failure policy |

## Composite assignments (alternatives, not extra simultaneous writers)
- [02 Data/prerequisites](02-data-prerequisites.md): combines features 01–03.
- [03 Ranking/explanation](03-ranking-explanation.md): combines features 04–05.
- [04 Web](04-web.md): web plus graph only when explicitly assigned.
- [05 Simulation/planning](05-simulation-roadmap.md): combines features 06–08.

Choose either composite ownership or the constituent individual feature assignments for a given file set. App routers, models, manifests and contracts each have one named writer. Use interfaces/fixtures for parallel work and verify actual integration afterward.

## Verification and additional work
- [06 Independent verification](06-verification.md).
- [07 Build/release](07-build-release.md).
- [08 Evidence audit](08-evidence-audit.md).
- [09 Research](09-research.md).

## v2 control improvements
Each task now states required input, proposed path boundary, public output, implementation steps, task-specific control, concrete acceptance/boundary cases, verification and handoff. Missing material policy blocks dependent work; routine reversible local choices use documented assumptions. Every handoff is DONE/PARTIAL/NEEDS_INPUT, with actual evidence and unrun checks.

Repository remains docs/architecture, docs/tasks, src/backend, src/web, src/prototype, test, build/deploy and tools. Prompts do not authorize broad edits, publication, real student-data use, or product infrastructure unrelated to scope.
