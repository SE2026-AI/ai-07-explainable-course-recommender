# Feature Agent Prompt — Multi-semester Roadmap (v2)

## Role, outcome and scope
You implement Multi-semester Roadmap for AI-07. Read common-context.md in full and the filled assignment-template.md before work. The human is PM/PO and primary developer, not assumed team leader. Your task is one bounded feature, not the entire project.
Outcome: implement the feature against accepted contracts, with evidence usable by the next consumer. Existing prototype is mock reference only.

## Required input packet
- Graph/plan interfaces; offering and semester definitions; objective/exclusion and bounded horizon schema.
- Assignment ticket/requirement IDs, workspace/commit, contract version/status and exact allowlist.
- Relevant docs/architecture files and fixtures/reference-scenarios.json.
- Current consumer interfaces and checks, not assumed files described only in old prompts.
Return NEEDS_INPUT for missing material semantics/interface. Propose options and proceed only with independent work; do not silently approve an architecture yourself.

## Write boundary
Proposed owned paths: src/backend/domain/roadmap.py; test/backend/test_roadmap.py; docs/architecture/PLANNING.md.
The envelope must enumerate actual assigned files; these suggestions are not permission to change adjacent code. Other domain features, prototype, pipeline, prompt files and contracts are read-only. API transport/shared schemas/manifests require explicit single ownership. No branch reset, push, merge, publication or new product infrastructure by default.

## Public output / contract
build_roadmap returning feasible/partial/infeasible with constraints and reasons.
Match the accepted schema exactly. If a needed field is missing, report a contract-change proposal with affected consumers/fixtures/tests instead of adding an undocumented field. Record version/provenance where contract requires it.

## Implementation sequence and decisions
1. Inspect current implementation and identify reusable code versus mock/proposed behavior.
2. Echo preflight: ticket, required inputs, readiness, allowed files, assumptions and checks.
3. Implement a minimal path using hand-verifiable fixture, then required boundaries.
4. Use prior-semester completions only. Compute dependency closure for target under approved policy, avoid repeats, respect credits/offerings/exclusions. Bound horizon and return diagnostics for missing availability, oversized requirement or unreachable target. Synthetic all-term offering is allowed only when adopted/labeled. No claim of global optimum or degree completion.
5. Verify relevant acceptance criteria, inspect failures, fix within scope and report unresolved gaps.

## Concrete reference acceptance
The shared fixture is illustrative until adopted; actual accepted policy wins.
BASE target DL401 with all-term fixture and limit 6 can use ST201 in term1, AI301 in term2, DL401 in term3; adding SE201 term1 is policy-dependent, not mandatory. Horizon2 cannot complete DL401. Limit3 cannot schedule 4-credit AI301. Excluded ST201 blocks target.

For every sentence above, express an observable Given/When/Then check and link its output to the assignment requirement ID. Add consumer-compatible examples, not merely prose asserting success.

## Boundary and failure inputs
Cycle; unavailable term; target already passed; zero horizon; missing offering; horizon exhaustion; no feasible next course.
Specify expected error/status/partial behavior from contract; unknown semantics are a dependency decision. Never treat malformed data as valid empty data or conceal a failed check.

## Verification control
Independent topological/order/credit checks plus hand-verified infeasible cases.
Derive expected values independently from rules/examples, not by copying the implementation. Use the repository's actual runtime/commands; do not invent installed dependencies. Record command, environment/revision, exit/result and test IDs. Mark unrun checks with reason. After fixes rerun affected checks and required integration checks. Do not weaken tests or expand scope to chase unrelated failures.

## Handoff / exit criteria
Web receives partial/valid roadmap and clear synthetic availability assumptions.
Use common-context's DONE/PARTIAL/NEEDS_INPUT format. Include changed files, interface, success/failure JSON or UI steps, acceptance-to-evidence map, actual checks, unrun checks, limitations and required next action. Record actual prompt/input/output in the assigned run log. DONE requires adopted criteria met and relevant checks passed; otherwise report the precise remaining work.
