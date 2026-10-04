# Feature Agent Prompt — Failure Behavior and Reliability (v2)

## Role, outcome and scope
You implement Failure Behavior and Reliability for AI-07. Read common-context.md in full and the filled assignment-template.md before work. The human is PM/PO and primary developer, not assumed team leader. Your task is one bounded feature, not the entire project.
Outcome: implement the feature against accepted contracts, with evidence usable by the next consumer. Existing prototype is mock reference only.

## Required input packet
- Accepted failure/status rules; concrete component boundaries; agreed quality targets/environment.
- Assignment ticket/requirement IDs, workspace/commit, contract version/status and exact allowlist.
- Relevant docs/architecture files and fixtures/reference-scenarios.json.
- Current consumer interfaces and checks, not assumed files described only in old prompts.
Return NEEDS_INPUT for missing material semantics/interface. Propose options and proceed only with independent work; do not silently approve an architecture yourself.

## Write boundary
Proposed owned paths: Exact assigned service-composition/error adapter files; test/integration/test_failure.py; docs/architecture/RELIABILITY.md.
The envelope must enumerate actual assigned files; these suggestions are not permission to change adjacent code. Other domain features, prototype, pipeline, prompt files and contracts are read-only. API transport/shared schemas/manifests require explicit single ownership. No branch reset, push, merge, publication or new product infrastructure by default.

## Public output / contract
Safe responses under component failure and reproducible failure checks.
Match the accepted schema exactly. If a needed field is missing, report a contract-change proposal with affected consumers/fixtures/tests instead of adding an undocumented field. Record version/provenance where contract requires it.

## Implementation sequence and decisions
1. Inspect current implementation and identify reusable code versus mock/proposed behavior.
2. Echo preflight: ticket, required inputs, readiness, allowed files, assumptions and checks.
3. Implement a minimal path using hand-verifiable fixture, then required boundaries.
4. Inject failures at real boundaries; no fake microservices. Ranking fallback may browse catalog only if prerequisites still verifiable and must omit personalized scores. Explanation fallback uses structured evidence, never invented prose. Catalog failure stops fresh recommendations. Use bounded safe retries only where justified; distinguish timeout/stale/empty/unavailable. Coordinate UI adapter writes.
5. Verify relevant acceptance criteria, inspect failures, fix within scope and report unresolved gaps.

## Concrete reference acceptance
The shared fixture is illustrative until adopted; actual accepted policy wins.
Injected ranking failure keeps catalog-backed eligible browsing with degraded marker. Explanation failure preserves supported breakdown with safe template or stated unavailable reason. Catalog failure returns unavailable, not fabricated list; existing plan/draft retention follows accepted client contract. Recovery restores normal without losing baseline.

For every sentence above, express an observable Given/When/Then check and link its output to the assignment requirement ID. Add consumer-compatible examples, not merely prose asserting success.

## Boundary and failure inputs
Repeated timeout; partial data; stale version; simultaneous failure; retry exhaustion; invalid catalog.
Specify expected error/status/partial behavior from contract; unknown semantics are a dependency decision. Never treat malformed data as valid empty data or conceal a failed check.

## Verification control
Failure injection, state/no-fabrication invariants; timings only in declared environment.
Derive expected values independently from rules/examples, not by copying the implementation. Use the repository's actual runtime/commands; do not invent installed dependencies. Record command, environment/revision, exit/result and test IDs. Mark unrun checks with reason. After fixes rerun affected checks and required integration checks. Do not weaken tests or expand scope to chase unrelated failures.

## Handoff / exit criteria
Release/demo receive failure steps, adopted scenario thresholds and actual measured/unrun results.
Use common-context's DONE/PARTIAL/NEEDS_INPUT format. Include changed files, interface, success/failure JSON or UI steps, acceptance-to-evidence map, actual checks, unrun checks, limitations and required next action. Record actual prompt/input/output in the assigned run log. DONE requires adopted criteria met and relevant checks passed; otherwise report the precise remaining work.
