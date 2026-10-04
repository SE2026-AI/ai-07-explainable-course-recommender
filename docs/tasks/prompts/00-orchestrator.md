# Root Orchestrator — v2

## Context and objective
Read docs/tasks/prompts/common-context.md in full, the completed assignment envelope, applicable repository instructions and relevant accepted decisions. AI-07 / SE2026-T24 / SE.2026.14. Human requester is PM/PO and primary developer, not assumed team leader. Explain in Vietnamese; technical artifacts in English.
Read the index and all shared controls; inventory existing code, mock prototype and design status. Do not infer accepted contracts from prompt plans. Establish task scope and output before spawning. When human instruction actually authorizes multi-agent execution, dispatch bounded specialists; otherwise prepare assignments without spawning.

## Required data and dependency gate
Human run objective, branch/revision, existing scope, repository instructions, current contracts and worker capacity.
Reinspect checkout; authoring-time prototype/backend status may have changed. Read docs/tasks/prompts/fixtures/reference-scenarios.json as illustrative data only. Accepted contract/policy supersedes fixture. Report exact missing input and propose options before dependent execution. Record revision and contract status, not just filenames.

## File/control boundary
Proposed output paths: docs/tasks/PRODUCT_BRIEF.md; BACKLOG.md; DELIVERY_PLAN.md; ASSIGNMENTS.md; AI_USAGE_LOG.md; assigned integration files only.
Assignment exact allowlist governs. Source, shared files, prompts and pipelines outside it are read-only. No branch reset, unrelated cleanup, external communication, publication, deployment or push without human authorization. Shared-file single ownership and real dependency readiness are mandatory.

## Work procedure
Plan increment1 catalog/profile/eligibility/ranking/explanation/API/web; increment2 isolated what-if and semester plan; increment3 roadmap/graph/reliability/release. Run architecture first if no accepted contract. Fill assignment envelopes with exact files, requirements, dependencies and fixtures. Use features/ prompts for small tickets; broad role prompts only for composite tasks, never concurrently overlapping. Web fixtures can run alongside backend after schema readiness. Data, ranking, explanation and planning can use accepted stub interfaces and independently verified fixtures; integration must replace stubs and recheck. Shared manifests/models/app/routers have one writer. Integrate vertical slices early, not after all modules finish. Keep assignment states PLANNED/DISPATCHED/BLOCKED/REVIEWED distinct.
Use inspect->bounded plan->execute->relevant verification->fix->handoff loop. Coordinate interface changes and consumers before changing schemas. Log actual used prompt and output; do not infer run evidence from plans.

## Task-specific controls and stop conditions
Gate A: coherent contracts and material assumptions reviewed; B: real core slice verified; C: immutable what-if and valid plan/roadmap; D: independent checks and reproducible setup. If an interface changes, update dependents/fixtures deliberately. Route defects to owner; do not erase uncommitted work. Record actual human decisions, not invented corrections.
Use common-context preflight, dependency and recovery controls. Continued independent work is allowed when dependent work needs a decision. Document reversible assumptions; do not silently invent academic policy.

## Concrete acceptance and boundaries
A profile lacking ST201 must never receive AI301 as recommendable now. A workload-priority scenario must reconcile .44/.82 fixture arithmetic when that component definition is adopted. Core UI calls real API with canonical fixture fields. Every active assignment has disjoint ownership or isolated integration plan.
Translate these into requirement-linked Given/When/Then checks where implementation is assigned. Include invalid/empty/ineligible inputs, not only a success demonstration. Designed fixture outputs are expected values, not results already achieved.

## Verification and review
Delegation authorized in current run; exact allowed files known; contract and dependency ready; no conflicting simultaneous writer.
Run only checks appropriate to the scope; record actual commands, environment, revision, results and unrun checks. Fix only within assignment. Unsupported claims must be labeled instead of passing by assertion.

## Required final handoff
A milestone status report and reviewable implementation/evidence, with publication/submission controlled by human authorization.
Return DONE/PARTIAL/NEEDS_INPUT with changed files, adopted/proposed assumptions, acceptance-to-evidence links, actual checks, limitations and exact next dependency. Do not self-approve material human decisions or declare all project work complete from this assignment.
