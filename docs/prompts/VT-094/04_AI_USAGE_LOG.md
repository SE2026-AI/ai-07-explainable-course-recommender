# AI Usage Log - VT-094

Tool: Codex coding agent in this conversation; Python/pytest/coverage/ruff/Git and actual localhost HTTP used for verification. Date2026-11-04. No external LLM/API/SMTP provider is used by the application patch.

Human prompt: "làm đi" with personal VT-094 assignment and Lecture06/07 PPTX. The following task prompts are the agent's recorded task instructions, not invented verbatim user messages:
- P1 `01_PLAN.md`: context/baseline/constraints/plan before implementation; output plan and assumptions retained with repository review.
- P2 `02_TEST_FIRST.md`: generate tests only, stop before implementation; output tests then genuine red run retained.
- P3 `03_CHANGE_VERIFY.md`: patch only after red, review scope/design/correctness/evidence; output bounded worker/validation retained after tests and diff check.

Revisions/rejections with evidence:
1. Reject changing v1 into a write/notification endpoint: api-contract section1 rule6 and recommendations.py::post_plan_check are read-only; standalone harness chosen under the assignment fallback.
2. Reject sending inside primary transaction or treating BackgroundTasks as capacity control: sender failure/latency must not affect primary work; explicit bounded queue after commit. Tests T01/T02/T03/T09/T14.
3. Reject status-only tests: T01 exact HUS/T03/max24 oracle kills wrong student_code mapping at3539c22, although HTTP remains200.
4. Correct plausible SQLite context assumption: `with connection` commits/rolls back but does not close. Initial run raised ResourceWarnings; explicit closing() removed these in accepted green log. Does not prove storage scales.
5. Reject claiming full delivery/production performance from green tests. Actual load logs disclose p95 failures and SQLite locking. Only local synthetic harness behavior was exercised.

Two plausible-but-untrustworthy AI patterns: happy-path/status-only assertion misses correct-shaped wrong mapping; cooperative asyncio timeout cannot constrain a synchronous/blocking sender. Coverage is scoped to harness and does not measure unexecuted production integrations.

Sources read: Lecture06 all27 slides (especially9-14,16-23,25-27); Lecture07 all28 slides (especially7-13,17-23,24-28). Examples about clinical appointments were not treated as project requirements.

Reflection and PDF text are AI-assisted drafts based on the recorded evidence; not an independent human review. Student must read/understand code and take responsibility before submitting. No peer approval, production guarantee or automatic Classroom submission is claimed.
