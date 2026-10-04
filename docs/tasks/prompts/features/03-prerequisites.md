# Feature Agent Prompt — Prerequisite Engine (v2)

## Role, outcome and scope
You implement Prerequisite Engine for AI-07. Read common-context.md in full and the filled assignment-template.md before work. The human is PM/PO and primary developer, not assumed team leader. Your task is one bounded feature, not the entire project.
Outcome: implement the feature against accepted contracts, with evidence usable by the next consumer. Existing prototype is mock reference only.

## Required input packet
- Validated catalog/profile interfaces; adopted AND and pass rules; graph result schema.
- Assignment ticket/requirement IDs, workspace/commit, contract version/status and exact allowlist.
- Relevant docs/architecture files and fixtures/reference-scenarios.json.
- Current consumer interfaces and checks, not assumed files described only in old prompts.
Return NEEDS_INPUT for missing material semantics/interface. Propose options and proceed only with independent work; do not silently approve an architecture yourself.

## Write boundary
Proposed owned paths: src/backend/domain/prerequisites.py; src/backend/domain/graph.py; test/backend/test_prerequisites.py.
The envelope must enumerate actual assigned files; these suggestions are not permission to change adjacent code. Other domain features, prototype, pipeline, prompt files and contracts are read-only. API transport/shared schemas/manifests require explicit single ownership. No branch reset, push, merge, publication or new product infrastructure by default.

## Public output / contract
eligibility, missing_direct, dependency_paths, conditional_unlocks.
Match the accepted schema exactly. If a needed field is missing, report a contract-change proposal with affected consumers/fixtures/tests instead of adding an undocumented field. Record version/provenance where contract requires it.

## Implementation sequence and decisions
1. Inspect current implementation and identify reusable code versus mock/proposed behavior.
2. Echo preflight: ticket, required inputs, readiness, allowed files, assumptions and checks.
3. Implement a minimal path using hand-verifiable fixture, then required boundaries.
4. Build edges prerequisite->dependent; detect cycles and missing references before traversal. Separate direct hard gate from transitive learning-path explanation and optional soft preparation. Recorded passing is not retroactively revoked by missing ancestors. Selecting a course is not completion. Bound traversal and deduplicate paths; define unknown-ID behavior. Do not edit scoring or UI.
5. Verify relevant acceptance criteria, inspect failures, fix within scope and report unresolved gaps.

## Concrete reference acceptance
The shared fixture is illustrative until adopted; actual accepted policy wins.
BASE: ST201/SE201 eligible, AI301 missing ST201, DL401 missing AI301. READY: AI301 eligible, DL401 not. FAILED cannot take ST201. Hypothetically completing ST201 unlocks AI301 only if CS101 is passed. A planned ST201 does not unlock AI301.

For every sentence above, express an observable Given/When/Then check and link its output to the assignment requirement ID. Add consumer-compatible examples, not merely prose asserting success.

## Boundary and failure inputs
Self-cycle; multi-node cycle; unknown node; multiple required parents; no prerequisites; partial unlock.
Specify expected error/status/partial behavior from contract; unknown semantics are a dependency decision. Never treat malformed data as valid empty data or conceal a failed check.

## Verification control
Hand-built DAG assertions; orientation; cycle/missing-reference checks; no mutation.
Derive expected values independently from rules/examples, not by copying the implementation. Use the repository's actual runtime/commands; do not invent installed dependencies. Record command, environment/revision, exit/result and test IDs. Mark unrun checks with reason. After fixes rerun affected checks and required integration checks. Do not weaken tests or expand scope to chase unrelated failures.

## Handoff / exit criteria
Ranking, explanation and planning receive eligibility/path fixtures.
Use common-context's DONE/PARTIAL/NEEDS_INPUT format. Include changed files, interface, success/failure JSON or UI steps, acceptance-to-evidence map, actual checks, unrun checks, limitations and required next action. Record actual prompt/input/output in the assigned run log. DONE requires adopted criteria met and relevant checks passed; otherwise report the precise remaining work.
