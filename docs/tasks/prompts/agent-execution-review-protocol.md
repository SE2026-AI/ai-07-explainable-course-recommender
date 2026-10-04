# Shared Agent Protocol — Execution Order, Review, Debugging and Evidence

Version: 1.0. Project: AI-07 — Explainable Course Recommender. Team SE2026-T24 / SE.2026.14.

Use this protocol with common-context.md, one task prompt and a filled assignment-template.md. This is a reusable instruction, not evidence that any task has run. The requester is PM/PO and primary developer; do not assume team leadership.

Explain progress and final findings in Vietnamese. Write code, comments, schemas and technical evidence documents in English. Human instructions and applicable repository instructions take precedence. No extra delegation, publication or repository-history changes are authorized by reading this file.

## 1. Mission

Implement a bounded task, then demonstrate that the change matches the project's adopted requirements and contracts. Make review and debugging reproducible: identify what changed, exactly where, why it changed, how it was checked, what remains uncertain and which downstream consumer is affected.

Your own implementation report is not independent acceptance. Distinguish local verification, independent review, integration verification and human acceptance.

## 2. Required preflight

Before edits, inspect and record:
- Task ID, requirement IDs, intended user outcome and explicit scope.
- Current workspace, branch, input commit and existing working changes.
- Task prompt/version and assignment envelope.
- Adopted contract/policy version and relevant architecture/decision files.
- Inputs, fixtures, upstream readiness, consumer interfaces and expected outputs.
- Exact assigned source/test/document/evidence paths and shared-file writers.
- Runtime/dependencies actually available and intended check commands.

Do not attribute pre-existing or concurrent edits to yourself. Record a pre-task diff/file baseline if changes are already present. A commit hash alone does not identify an uncommitted checkout: record the relevant diff or patch plus versions. Never discard another worker's changes.

If an input is missing, distinguish a routine reversible choice from a material domain/contract decision. Document routine defaults. For a material gap, report NEEDS_INPUT, exact missing information, options and unaffected work. Do not invent academic policy or silently accept a proposed fixture.

## 3. Task and agent order

Roles below describe responsibilities; a role can run serially or be reused. Use actual platform capacity and human-authorized delegation. Do not launch every role at once.

| Stage | Task prompt / role | Prerequisite | Ready-to-handoff evidence |
|---|---|---|---|
| A | Product/backlog | Official scope and repo inspected | Outcomes, IDs, success/failure AC and proposed increments |
| B | Architecture | Product scope ready | Adopted schema/interfaces/policies, consistent examples, unresolved decisions explicit |
| C | Dispatch/orchestrator | Task boundaries and contract version ready | Exact allowlists, writer ownership, dependency map and fixtures |
| D1 | Catalog then profile/goals | Adopted schemas and units | Validated reference data and state semantics |
| D2 | Web shell/mock adapter, parallel with D1 | Same adopted API fixtures | Labeled mock flow; no second domain engine |
| E | Prerequisite engine | Catalog/profile interface ready | Eligibility/path/cycle checks and consumer examples |
| F | Ranking | Eligibility and scoring policy ready | Independent arithmetic, stable ranking and breakdown |
| G | Explanation | Ranking/path/evidence outputs ready | Why/why-not grounded in real data |
| H | Core API integration + live Web | Required domain interfaces ready | Real profile->recommendation->reason flow; fixture/live contract alignment |
| I1 | What-if then semester plan | Canonical engine and scenario/constraint contracts | Immutable baseline, deltas and credit/eligibility checks |
| I2 | Graph UI, parallel when files disjoint | Graph API and web shell ready | Correct edge/status display and text alternative |
| J | Roadmap | Graph/planning/offerings/horizon policy ready | Valid/partial/infeasible roadmap with ordering and credit evidence |
| K | Reliability and integrated verification | Actual feature boundaries ready | Reproducible injected failures and safe response checks |
| L | Build/release preparation and evidence audit | Required checks/reviews complete | Clean setup or explicit limitation, traceability, demo and evidence |

Independent review/tests happen after each bounded feature, not only stage K. Integration is repeated at each usable slice. A stage returning a defect routes a fix to the responsible owner, then relevant checks and consumer integration are rerun.

After adopted interfaces exist, a consumer may develop with contract-valid fixtures while the producer is incomplete. Mark this MOCK_DEPENDENCY; it does not satisfy live integration. Never change the fixture to hide producer/consumer disagreement.

Catalog/profile can parallelize only with disjoint files and known cross-validation ownership. Ranking/explanation or simulation/planning can parallelize using accepted interfaces, but only when mock readiness, separate ownership and later integration are explicit. Otherwise follow dependency order.

## 4. Shared-file and scope control

Preserve docs/architecture, docs/tasks, src/backend, src/web, src/prototype, test, build/deploy and tools.

One writer owns each shared schema, router, application entrypoint, manifest and canonical fixture. Feature agents primarily write assigned domain/component files. Reviewers read source and report findings; testers write only assigned test/evidence files. An owner handles source fixes unless a fix ticket transfers exact ownership.

A contract change needs a proposal listing reason, old/new example, compatibility, consumers, fixture/tests affected and migration approach. Obtain the required product decision before dependent work; do not silently rewrite consumers.

Prefer narrow edits. Do not perform unrelated cleanup, remove failing checks or broaden the product scope to make a task appear complete.

## 5. Implement and self-review

Work loop: inspect -> minimal change -> inspect diff -> check -> diagnose -> focused fix -> relevant recheck -> handoff.

Review your own diff against:
- Assigned outcome and Given/When/Then criteria.
- Contract fields, units, status/error behavior and versions.
- Academic invariants in common-context.md.
- Evidence/reason grounding and score arithmetic.
- Baseline/state mutation, async response ordering and failure paths where relevant.
- Allowed paths, shared-file ownership and unintended changes.
- Missing boundary cases and consumers affected.

Inspect actual code/files after the final edit. A test pass before the final edit is not evidence for the final state. Avoid repeated broad test runs once relevant checks pass unless changes or unresolved risks justify them.

## 6. Show exact change locations

Produce a change map:

| Requirement / task | Path | Symbol / endpoint / UI component | Current line anchor | Before -> after | Consumer impact |
|---|---|---|---|---|---|
| Actual ID | Actual relative repo path | Actual function/class/route | Verified line and input/output revision | Concrete behavior | Actual consumers |

Record line numbers from the inspected final file; do not guess. Pair line anchors with symbols and revision because lines move. In user-facing replies use clickable absolute local file links when available. In portable repository evidence use repo-relative paths plus revision/symbol.

For a new file, mark NEW rather than inventing a previous behavior. For pre-existing defects, distinguish changed and unchanged locations. A directory-only reference is insufficient when an actual function or endpoint can be identified.

Keep a patch/diff artifact or committed revision for reproducibility. If no commit is authorized, leave work uncommitted and save the task diff/owned-file snapshot at the assigned evidence path. Do not commit automatically just to obtain an identifier.

## 7. Test and project reconciliation

Create an acceptance evidence matrix:

| Outcome | Requirement | AC | Test / scenario ID | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|---|

Statuses: PASS / FAIL / UNRUN / NOT_APPLICABLE with justification. An unsupported assumption is not PASS. Use adopted requirements; illustrative scenarios must be labeled if policy is not yet adopted.

Check the relevant layers:
1. Domain: invariants and independent arithmetic/examples.
2. Contract: schema, fixture and actual response consistency.
3. Integration: producer-consumer interaction with real implementations.
4. UI: observable user path, keyboard/responsive/error states when applicable.
5. Quality: declared environment and measurements only where required.

For AI-07, select relevant cases from:
- BASE cannot take AI301 because ST201 is missing.
- FAILED does not pass MA101; planned ST201 is not completed.
- Scores/contributions reconcile and deterministic ties remain stable.
- Priority changes reverse the illustrative ST201/SE201 order under adopted fixture components.
- Why-not names actual missing prerequisites; unlock claims account for every parent.
- What-if leaves baseline unchanged and differentiates entrants/exits from rank changes.
- Plan never exceeds credits or includes duplicate/ineligible/completed courses.
- Roadmap uses prior-semester completions, offerings and bounded horizon.
- Degraded/unavailable responses do not fabricate personalized results.

Synthetic data demonstrates logic, not real-world academic effectiveness. Do not fabricate user study, load/latency, browser coverage or recommendation accuracy.

Every executed check records command or manual steps, input data/version, environment, timestamp, exit/result and concise output. Store logs/assertions/request-response evidence. Screenshots demonstrate visible UI behavior; they do not prove backend invariants alone. Redact secrets and use synthetic identities.

## 8. Independent reviewer and tester

When independently assigned, the reviewer/tester receives: original task/prompt, adopted requirement/contract, input and final revision or patch, change map, fixtures and author evidence.

Reviewer: verify scope, invariants, contracts and plausible failure behavior. Findings must be actionable and cite code locations. Do not approve merely because author tests pass.

Tester: derive expected values from requirements or hand-verifiable data, not copied implementation. Reproduce the claimed flow and boundaries. Keep source read-only unless explicitly assigned a fix. Report environment failures separately from product failures.

If no independent worker or human review exists, say INDEPENDENT_REVIEW_PENDING. Never represent self-review or a reused author session as independent review. Review/test roles do not authorize spawning new agents by themselves.

## 9. Debugging and defect format

For each defect, record:
- Defect ID, severity and requirement/AC.
- Observed revision, fixture/version and environment.
- Exact reproduction steps or command/request.
- Expected versus actual behavior.
- Log/response/assertion/screenshot evidence path.
- Failing path/symbol/verified line when known.
- Root-cause hypothesis and supporting evidence; label hypothesis unconfirmed.
- Owning module and affected consumers.
- Smallest proposed fix and regression check.

Triage: input/data issue; domain rule; scoring/explanation; contract/version; UI/state; integration; environment/dependency. Do not patch every layer when the cause is in one producer.

Fix process: reproduce -> isolate -> change within owner scope -> rerun original failure -> run affected regressions/consumer checks -> inspect final diff -> update evidence. Mark FIXED_VERIFIED only after a confirming run; otherwise FIXED_UNVERIFIED or OPEN.

After two identical failed attempts without new evidence, stop repeating the same approach, report cause/blocker and an alternative, and continue independent work. Do not weaken tests or swallow errors to obtain green output.

## 10. Evidence files

Use one actual run ID and assigned allowlist, for example:

```text
docs/tasks/runs/<run-id>/
  REPORT.md
  CHANGE_MAP.md
  ACCEPTANCE.md
  DEFECTS.md
  PROMPT_USED.md
  evidence/
    <actual logs, response examples, screenshots or patch>
```

Do not generate empty placeholder evidence and claim completion. A small task may consolidate tables into REPORT.md while preserving links to actual artifacts. Evidence describes observed state, not promised future checks.

Record actual prompt/envelope and meaningful AI output excerpt. Keep/edit/reject decisions must reflect real review; do not manufacture corrections for grading. Model/tool identity may be UNKNOWN when unavailable.

## 11. Completion and next-agent gate

Task status: DONE / PARTIAL / NEEDS_INPUT, separate from review status: SELF_REVIEWED / INDEPENDENT_REVIEW_PENDING / REVIEW_PASSED / CHANGES_REQUESTED, and integration status: MOCK_ONLY / LIVE_VERIFIED / INTEGRATION_PENDING.

DONE means scoped adopted AC met, relevant checks pass, diff reviewed and documentation/contract consumer obligations fulfilled. It does not imply independent acceptance or project completion. Pending required checks/decisions yield PARTIAL or NEEDS_INPUT.

Next dependent agent starts when its needed interface, fixture/version and ownership are ready. It may use a declared mock dependency if allowed, but the final integration gate remains open. New code or contract changes can invalidate earlier evidence; rerun affected checks.

## 12. Required final reply

Lead with status and observable result, then provide:
1. Task/requirement, branch/revision and contract.
2. Change map with exact file/symbol/line links and before/after behavior.
3. Acceptance-to-test evidence with actual results.
4. Defects found/fixed/open, repro and root-cause confidence.
5. Unrun checks, remaining assumptions and limitations.
6. Review/integration status and exact handoff prerequisite for the next task.
7. Evidence report path.

Do not conclude merely 'done, tests passed'. Make it possible for another person to reproduce the behavior and locate the responsible code without reading the full chat.
