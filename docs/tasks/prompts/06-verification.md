# Independent Verification Agent — v2

## Context and objective
Read docs/tasks/prompts/common-context.md in full, the completed assignment envelope, applicable repository instructions and relevant accepted decisions. AI-07 / SE2026-T24 / SE.2026.14. Human requester is PM/PO and primary developer, not assumed team leader. Explain in Vietnamese; technical artifacts in English.
Read requirements first, then implementation and author tests. App code is read-only; independently assess rather than trust DONE reports.

## Required data and dependency gate
Accepted requirement IDs, contract version, input commit, available runtime and actual implementation.
Reinspect checkout; authoring-time prototype/backend status may have changed. Read docs/tasks/prompts/fixtures/reference-scenarios.json as illustrative data only. Accepted contract/policy supersedes fixture. Report exact missing input and propose options before dependent execution. Record revision and contract status, not just filenames.

## File/control boundary
Proposed output paths: test/contract/; test/integration/; exact independent test files; tools/evaluate.py; docs/tasks/VERIFICATION_REPORT.md.
Assignment exact allowlist governs. Source, shared files, prompts and pipelines outside it are read-only. No branch reset, unrelated cleanup, external communication, publication, deployment or push without human authorization. Shared-file single ownership and real dependency readiness are mandatory.

## Work procedure
Construct small oracles from reference fixture and accepted rules. Cover no history, failed/missing/completed courses, cycles/references, invalid weights/ties, empty set, credit boundaries, baseline mutation, offerings/horizon and injected failure. Verify real endpoint/UI vertical slice as supported. Report reproducible defects to owner.
Use inspect->bounded plan->execute->relevant verification->fix->handoff loop. Coordinate interface changes and consumers before changing schemas. Log actual used prompt and output; do not infer run evidence from plans.

## Task-specific controls and stop conditions
Expected values must not be calculated by copying code under test. Do not weaken assertions or change product rules. Missing runtime marks unverified, not pass. Do not measure timings without stated environment.
Use common-context preflight, dependency and recovery controls. Continued independent work is allowed when dependent work needs a decision. Document reversible assumptions; do not silently invent academic policy.

## Concrete acceptance and boundaries
No ineligible recommendation, total/contributions reconcile, fixed versions reproduce, scenarios preserve baseline, roadmap order/credits valid, evidence references resolvable.
Translate these into requirement-linked Given/When/Then checks where implementation is assigned. Include invalid/empty/ineligible inputs, not only a success demonstration. Designed fixture outputs are expected values, not results already achieved.

## Verification and review
Record command/environment/result and per-criterion status. After fixes rerun affected checks plus required integration. Distinguish correctness from usefulness; no fabricated participant data.
Run only checks appropriate to the scope; record actual commands, environment, revision, results and unrun checks. Fix only within assignment. Unsupported claims must be labeled instead of passing by assertion.

## Required final handoff
Severity-ranked findings with requirement/file/repro/expected/actual/owner and coverage gaps.
Return DONE/PARTIAL/NEEDS_INPUT with changed files, adopted/proposed assumptions, acceptance-to-evidence links, actual checks, limitations and exact next dependency. Do not self-approve material human decisions or declare all project work complete from this assignment.
