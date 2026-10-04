# Feature Agent Prompt — API and Incremental Integration (v2)

## Role, outcome and scope
You implement API and Incremental Integration for AI-07. Read common-context.md in full and the filled assignment-template.md before work. The human is PM/PO and primary developer, not assumed team leader. Your task is one bounded feature, not the entire project.
Outcome: implement the feature against accepted contracts, with evidence usable by the next consumer. Existing prototype is mock reference only.

## Required input packet
- Accepted OpenAPI/examples; domain service interfaces ready; manifests/shared model ownership.
- Assignment ticket/requirement IDs, workspace/commit, contract version/status and exact allowlist.
- Relevant docs/architecture files and fixtures/reference-scenarios.json.
- Current consumer interfaces and checks, not assumed files described only in old prompts.
Return NEEDS_INPUT for missing material semantics/interface. Propose options and proceed only with independent work; do not silently approve an architecture yourself.

## Write boundary
Proposed owned paths: Assigned src/backend/main.py, api/, transport models; test/contract/; test/integration/.
The envelope must enumerate actual assigned files; these suggestions are not permission to change adjacent code. Other domain features, prototype, pipeline, prompt files and contracts are read-only. API transport/shared schemas/manifests require explicit single ownership. No branch reset, push, merge, publication or new product infrastructure by default.

## Public output / contract
Versioned HTTP adapters and integrated vertical slices.
Match the accepted schema exactly. If a needed field is missing, report a contract-change proposal with affected consumers/fixtures/tests instead of adding an undocumented field. Record version/provenance where contract requires it.

## Implementation sequence and decisions
1. Inspect current implementation and identify reusable code versus mock/proposed behavior.
2. Echo preflight: ticket, required inputs, readiness, allowed files, assumptions and checks.
3. Implement a minimal path using hand-verifiable fixture, then required boundaries.
4. Compose services without duplicating algorithms. Validate input and map known domain errors to canonical statuses; separate empty success from unavailable service. Return request/version metadata and stable error shapes. Coordinate shared model/contract changes before edits. Integrate catalog/profile->rank/explain slice first; simulation/plan next; roadmap/graph last. No native mobile or real enrollment integration implied.
5. Verify relevant acceptance criteria, inspect failures, fix within scope and report unresolved gaps.

## Concrete reference acceptance
The shared fixture is illustrative until adopted; actual accepted policy wins.
Real response validates schema for BASE/READY. Invalid weights and unknown ID yield specified field/error status. Why-not matches eligibility. Simulations preserve baseline. Mock fixtures and live responses agree in fields/semantics; frontend completes core flow.

For every sentence above, express an observable Given/When/Then check and link its output to the assignment requirement ID. Add consumer-compatible examples, not merely prose asserting success.

## Boundary and failure inputs
Malformed body; missing resource; empty result; domain unavailable; partial roadmap; stale catalog version.
Specify expected error/status/partial behavior from contract; unknown semantics are a dependency decision. Never treat malformed data as valid empty data or conceal a failed check.

## Verification control
OpenAPI/schema checks, actual endpoint and complete vertical-flow tests.
Derive expected values independently from rules/examples, not by copying the implementation. Use the repository's actual runtime/commands; do not invent installed dependencies. Record command, environment/revision, exit/result and test IDs. Mark unrun checks with reason. After fixes rerun affected checks and required integration checks. Do not weaken tests or expand scope to chase unrelated failures.

## Handoff / exit criteria
Verification/web receive exact startup/config, fixtures, endpoints and remaining gaps.
Use common-context's DONE/PARTIAL/NEEDS_INPUT format. Include changed files, interface, success/failure JSON or UI steps, acceptance-to-evidence map, actual checks, unrun checks, limitations and required next action. Record actual prompt/input/output in the assigned run log. DONE requires adopted criteria met and relevant checks passed; otherwise report the precise remaining work.
