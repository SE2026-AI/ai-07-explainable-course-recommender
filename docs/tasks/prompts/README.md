# AI-07 prompt index

Team: SE2026-T24 / SE.2026.14. Human lead: PM/PO and primary developer.

Start with [team pipeline and responsibilities](../TEAM_PIPELINE.md). This file explains the human responsibilities and runtime/development order in Vietnamese.

## Shared files
- [Common context](common-context.md): include with every specialist prompt.
- [Assignment template](assignment-template.md): fill exact task, contract version, dependencies, allowed files and checks.
- [Orchestrator](00-orchestrator.md): root multi-agent coordination.

## Architecture and management
- [Architecture and contracts](01-architecture.md).
- [Product/backlog](management/01-product-backlog.md).
- [Task decomposition/dispatch](management/02-task-dispatch.md).
- [Review/change request](management/03-review-change.md).

## Feature prompts
| File | Feature |
|---|---|
| [01](features/01-catalog.md) | Course catalog |
| [02](features/02-profile-goals.md) | Synthetic profile and goals |
| [03](features/03-prerequisites.md) | Prerequisites and eligibility |
| [04](features/04-ranking.md) | Ranking and weight controls |
| [05](features/05-explanations.md) | Why/why-not and evidence |
| [06](features/06-what-if.md) | Baseline/scenario comparison |
| [07](features/07-semester-plan.md) | Credit-constrained semester plan |
| [08](features/08-roadmap.md) | Multi-semester roadmap |
| [09](features/09-graph-ui.md) | Graph visualization |
| [10](features/10-web.md) | Web user flow |
| [11](features/11-api-integration.md) | API/application integration |
| [12](features/12-reliability.md) | Failure handling and reliability |

## Verification, release and evidence
- [Independent verification](06-verification.md).
- [Build/release preparation](07-build-release.md).
- [Evidence/prompt audit](08-evidence-audit.md).

## Existing broad role prompts
02-data-prerequisites.md, 03-ranking-explanation.md, 04-web.md and 05-simulation-roadmap.md remain available for larger assignments. Prefer the feature-specific prompts for small tickets. A broad role and its feature prompts are alternatives; do not concurrently assign overlapping ownership.

## Run instructions
Send common-context.md + one task prompt + the completed assignment template. Orchestrator reads this index and TEAM_PIPELINE.md to choose prompts. Contract-ready web fixture work may run alongside backend domain work with disjoint file ownership. Domain features do not own HTTP routers by default; integration owns shared app/schema/transport composition.

Use docs/architecture, docs/tasks, src/backend, src/web, test, build/deploy and tools as defined by TEAM_PIPELINE.md. Preserve src/prototype. Actual prompts/output/review/results go to docs/tasks/runs/<run-id>.md when a run occurs.

These files are reusable prompt plans. Creating them does not mean any specialist has executed, implementation has completed, or checks have passed.
