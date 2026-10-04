# Composite Web Agent — v2

## Context and objective
Read docs/tasks/prompts/common-context.md in full, the completed assignment envelope, applicable repository instructions and relevant accepted decisions. AI-07 / SE2026-T24 / SE.2026.14. Human requester is PM/PO and primary developer, not assumed team leader. Explain in Vietnamese; technical artifacts in English.
Use feature prompts as detailed criteria. Do not create a competing app or client-side canonical recommender.

## Required data and dependency gate
OpenAPI/examples, web layout, feature 10-web; feature 09-graph-ui when assigned.
Reinspect checkout; authoring-time prototype/backend status may have changed. Read docs/tasks/prompts/fixtures/reference-scenarios.json as illustrative data only. Accepted contract/policy supersedes fixture. Report exact missing input and propose options before dependent execution. Record revision and contract status, not just filenames.

## File/control boundary
Proposed output paths: Assigned src/web files and test/web tests; graph files only if explicitly included.
Assignment exact allowlist governs. Source, shared files, prompts and pipelines outside it are read-only. No branch reset, unrelated cleanup, external communication, publication, deployment or push without human authorization. Shared-file single ownership and real dependency readiness are mandatory.

## Work procedure
Build fixture-backed adapter and core journey; replace with live endpoints incrementally. Then add comparison/plan/roadmap and graph as contracts become ready. Keep one manifest owner and explicit mock label.
Use inspect->bounded plan->execute->relevant verification->fix->handoff loop. Coordinate interface changes and consumers before changing schemas. Log actual used prompt and output; do not infer run evidence from plans.

## Task-specific controls and stop conditions
No UI placeholder presented as live calculation. Responses are checked against current request identity; stale scenario results cannot win races. Do not edit backend or contracts to make frontend guesses work.
Use common-context preflight, dependency and recovery controls. Continued independent work is allowed when dependent work needs a decision. Document reversible assumptions; do not silently invent academic policy.

## Concrete acceptance and boundaries
BASE blocked AI301; exact credits; unchanged baseline; latest request wins; invalid input and unavailable API visible; keyboard/narrow/wide review documented.
Translate these into requirement-linked Given/When/Then checks where implementation is assigned. Include invalid/empty/ineligible inputs, not only a success demonstration. Designed fixture outputs are expected values, not results already achieved.

## Verification and review
UI flow tests and actual browser checks; describe absent device/platform coverage.
Run only checks appropriate to the scope; record actual commands, environment, revision, results and unrun checks. Fix only within assignment. Unsupported claims must be labeled instead of passing by assertion.

## Required final handoff
Mock/live startup, typed adapter/component interfaces, evidence and limitations.
Return DONE/PARTIAL/NEEDS_INPUT with changed files, adopted/proposed assumptions, acceptance-to-evidence links, actual checks, limitations and exact next dependency. Do not self-approve material human decisions or declare all project work complete from this assignment.
