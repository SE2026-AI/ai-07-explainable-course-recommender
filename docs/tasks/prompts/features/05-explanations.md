# Feature Agent Prompt — Why / Why-not Explanations (v2)

## Role, outcome and scope
You implement Why / Why-not Explanations for AI-07. Read common-context.md in full and the filled assignment-template.md before work. The human is PM/PO and primary developer, not assumed team leader. Your task is one bounded feature, not the entire project.
Outcome: implement the feature against accepted contracts, with evidence usable by the next consumer. Existing prototype is mock reference only.

## Required input packet
- Eligibility/path and score outputs; evidence/provenance schema; supported reason codes.
- Assignment ticket/requirement IDs, workspace/commit, contract version/status and exact allowlist.
- Relevant docs/architecture files and fixtures/reference-scenarios.json.
- Current consumer interfaces and checks, not assumed files described only in old prompts.
Return NEEDS_INPUT for missing material semantics/interface. Propose options and proceed only with independent work; do not silently approve an architecture yourself.

## Write boundary
Proposed owned paths: src/backend/domain/explanation.py; test/backend/test_explanation.py.
The envelope must enumerate actual assigned files; these suggestions are not permission to change adjacent code. Other domain features, prototype, pipeline, prompt files and contracts are read-only. API transport/shared schemas/manifests require explicit single ownership. No branch reset, push, merge, publication or new product infrastructure by default.

## Public output / contract
explain_recommendation, explain_why_not with reasons/warnings/evidence.
Match the accepted schema exactly. If a needed field is missing, report a contract-change proposal with affected consumers/fixtures/tests instead of adding an undocumented field. Record version/provenance where contract requires it.

## Implementation sequence and decisions
1. Inspect current implementation and identify reusable code versus mock/proposed behavior.
2. Echo preflight: ticket, required inputs, readiness, allowed files, assumptions and checks.
3. Implement a minimal path using hand-verifiable fixture, then required boundaries.
4. Generate reasons only from current data and actual component contributions. Differentiate completed, ineligible, eligible-but-low-ranked and excluded by plan budget. Keep evidence references resolvable to catalog/profile/version. Conditional future unlocks must check all parents. Describe workload as estimated synthetic hours, not measured burden. Deterministic templates first; no unsolicited LLM.
5. Verify relevant acceptance criteria, inspect failures, fix within scope and report unresolved gaps.

## Concrete reference acceptance
The shared fixture is illustrative until adopted; actual accepted policy wins.
BASE AI301 why-not names ST201; DL401 names AI301 directly and can show transitive ST201 path. ST201 .86 breakdown reconciles .8 goal + .06 workload. Workload scenario updates explanation from changed contributions. Completing ST201 without CS101 cannot claim AI301 fully unlocked.

For every sentence above, express an observable Given/When/Then check and link its output to the assignment requirement ID. Add consumer-compatible examples, not merely prose asserting success.

## Boundary and failure inputs
Absent evidence; stale versions; score mismatch; no candidate; missing policy; low-ranked vs blocked.
Specify expected error/status/partial behavior from contract; unknown semantics are a dependency decision. Never treat malformed data as valid empty data or conceal a failed check.

## Verification control
Evidence-reference checks, contribution reconciliation and contradictory-reason tests.
Derive expected values independently from rules/examples, not by copying the implementation. Use the repository's actual runtime/commands; do not invent installed dependencies. Record command, environment/revision, exit/result and test IDs. Mark unrun checks with reason. After fixes rerun affected checks and required integration checks. Do not weaken tests or expand scope to chase unrelated failures.

## Handoff / exit criteria
Web/API receive successful, rejected and budget-excluded explanation fixtures.
Use common-context's DONE/PARTIAL/NEEDS_INPUT format. Include changed files, interface, success/failure JSON or UI steps, acceptance-to-evidence map, actual checks, unrun checks, limitations and required next action. Record actual prompt/input/output in the assigned run log. DONE requires adopted criteria met and relevant checks passed; otherwise report the precise remaining work.
