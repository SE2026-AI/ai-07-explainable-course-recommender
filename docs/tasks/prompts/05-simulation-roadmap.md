# Composite Simulation and Planning Agent — v2

## Context and objective
Read docs/tasks/prompts/common-context.md in full, the completed assignment envelope, applicable repository instructions and relevant accepted decisions. AI-07 / SE2026-T24 / SE.2026.14. Human requester is PM/PO and primary developer, not assumed team leader. Explain in Vietnamese; technical artifacts in English.
Use only for composite ownership; read all three detailed feature prompts.

## Required data and dependency gate
Ranking/eligibility contracts, availability and horizon policy; features 06, 07, 08.
Reinspect checkout; authoring-time prototype/backend status may have changed. Read docs/tasks/prompts/fixtures/reference-scenarios.json as illustrative data only. Accepted contract/policy supersedes fixture. Report exact missing input and propose options before dependent execution. Record revision and contract status, not just filenames.

## File/control boundary
Proposed output paths: Assigned simulation/planning/roadmap domain files, related tests, PLANNING.md.
Assignment exact allowlist governs. Source, shared files, prompts and pipelines outside it are read-only. No branch reset, unrelated cleanup, external communication, publication, deployment or push without human authorization. Shared-file single ownership and real dependency readiness are mandatory.

## Work procedure
Implement immutable scenario first, then semester constraints, then bounded roadmap. Call canonical ranking/graph instead of duplicated business logic. HTTP adapters belong to integration owner.
Use inspect->bounded plan->execute->relevant verification->fix->handoff loop. Coordinate interface changes and consumers before changing schemas. Log actual used prompt and output; do not infer run evidence from plans.

## Task-specific controls and stop conditions
Stop for undefined availability/semester/credit policy. Never interpret planned completion as same-semester pass; never claim optimality. Validate baseline/version before comparison.
Use common-context preflight, dependency and recovery controls. Continued independent work is allowed when dependent work needs a decision. Document reversible assumptions; do not silently invent academic policy.

## Concrete acceptance and boundaries
Fixture weight reversal leaves baseline intact; ST201+SE201 exactly6; AI301 needs earlier ST201; BASE->DL401 requires at least3 fixture terms; limit3/horizon2 report infeasible.
Translate these into requirement-linked Given/When/Then checks where implementation is assigned. Include invalid/empty/ineligible inputs, not only a success demonstration. Designed fixture outputs are expected values, not results already achieved.

## Verification and review
Independent immutability/credit/topological checks with valid and partial fixtures.
Run only checks appropriate to the scope; record actual commands, environment, revision, results and unrun checks. Fix only within assignment. Unsupported claims must be labeled instead of passing by assertion.

## Required final handoff
Before/after, valid/infeasible plans and dependency-ready outputs.
Return DONE/PARTIAL/NEEDS_INPUT with changed files, adopted/proposed assumptions, acceptance-to-evidence links, actual checks, limitations and exact next dependency. Do not self-approve material human decisions or declare all project work complete from this assignment.
