# Feature Agent Prompt — What-if Simulation (v2)

## Role, outcome and scope
You implement What-if Simulation for AI-07. Read common-context.md in full and the filled assignment-template.md before work. The human is PM/PO and primary developer, not assumed team leader. Your task is one bounded feature, not the entire project.
Outcome: implement the feature against accepted contracts, with evidence usable by the next consumer. Existing prototype is mock reference only.

## Required input packet
- Baseline/profile versions; canonical ranking and eligibility interfaces; scenario schema.
- Assignment ticket/requirement IDs, workspace/commit, contract version/status and exact allowlist.
- Relevant docs/architecture files and fixtures/reference-scenarios.json.
- Current consumer interfaces and checks, not assumed files described only in old prompts.
Return NEEDS_INPUT for missing material semantics/interface. Propose options and proceed only with independent work; do not silently approve an architecture yourself.

## Write boundary
Proposed owned paths: src/backend/domain/simulation.py; test/backend/test_simulation.py.
The envelope must enumerate actual assigned files; these suggestions are not permission to change adjacent code. Other domain features, prototype, pipeline, prompt files and contracts are read-only. API transport/shared schemas/manifests require explicit single ownership. No branch reset, push, merge, publication or new product infrastructure by default.

## Public output / contract
simulate(baseline,changes) with delta and scenario-only state.
Match the accepted schema exactly. If a needed field is missing, report a contract-change proposal with affected consumers/fixtures/tests instead of adding an undocumented field. Record version/provenance where contract requires it.

## Implementation sequence and decisions
1. Inspect current implementation and identify reusable code versus mock/proposed behavior.
2. Echo preflight: ticket, required inputs, readiness, allowed files, assumptions and checks.
3. Implement a minimal path using hand-verifiable fixture, then required boundaries.
4. Clone inputs; validate changes; recompute through canonical engine. Keep excluded/planned/hypothetically completed separate. Compare ranks on defined common set; report entrants/exits and eligibility separately instead of misleading rank subtraction. Same input/version gives same output. No automatic persistence. UI async race management belongs to web.
5. Verify relevant acceptance criteria, inspect failures, fix within scope and report unresolved gaps.

## Concrete reference acceptance
The shared fixture is illustrative until adopted; actual accepted policy wins.
Switch reference weights from .8/.2 to .2/.8: ST201 score .86->.44; SE201 .58->.82 and order changes. Baseline weights/history remain unchanged. Hypothetical ST201 makes AI301 eligible for BASE scenario only. Reset reproduces baseline.

For every sentence above, express an observable Given/When/Then check and link its output to the assignment requirement ID. Add consumer-compatible examples, not merely prose asserting success.

## Boundary and failure inputs
Invalid weights/change key; baseline version mismatch; new eligibility; empty comparison; concurrent independent scenarios.
Specify expected error/status/partial behavior from contract; unknown semantics are a dependency decision. Never treat malformed data as valid empty data or conceal a failed check.

## Verification control
Snapshot baseline before/after, independent delta arithmetic and scenario repeatability.
Derive expected values independently from rules/examples, not by copying the implementation. Use the repository's actual runtime/commands; do not invent installed dependencies. Record command, environment/revision, exit/result and test IDs. Mark unrun checks with reason. After fixes rerun affected checks and required integration checks. Do not weaken tests or expand scope to chase unrelated failures.

## Handoff / exit criteria
Web/planning receive baseline/scenario fixtures and precise rank comparison semantics.
Use common-context's DONE/PARTIAL/NEEDS_INPUT format. Include changed files, interface, success/failure JSON or UI steps, acceptance-to-evidence map, actual checks, unrun checks, limitations and required next action. Record actual prompt/input/output in the assigned run log. DONE requires adopted criteria met and relevant checks passed; otherwise report the precise remaining work.
