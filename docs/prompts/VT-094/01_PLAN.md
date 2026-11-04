# Prompt P1 - plan before implementation

Role: coding agent assisting individual student Dinh Truong An, 22001535, member of SE2026-T24.
Task: BT3 AI-07 VT-094. Add a notification for one business event; notification failure must not undo the primary transaction. Risk: large input timeout/performance regression. Mandatory equivalence partitioning, response-field mapping mutation, 100 concurrent tasks, p95 <=3.0s. Generate tests BEFORE notification implementation and verify the red reason.

Repository baseline: 2cbda6b3ebb203b8be1dd664ab60564311be922e.
Read src/api/routers/recommendations.py::post_plan_check, schemas/recommendations.py, rules/plan.py, docs/architecture/api-contract.md sections 1 and 7. Existing v1 is read-only, deterministic, synthetic-only. There is no notification transport or business write endpoint. Do not change public v1, its DB, or introduce SMTP credentials.

Output required: assumptions, small vertical slice, exact files, test-first steps, risks and rejected alternatives. Allowed fallback: executable harness around the nearest real module, with honest limits. Keep branch separate and do not merge.

## AI plan output (recorded before notification code)

1. Build a separate experimental plan-check harness, reuse real post_plan_check/rules/explanation; synthetic Repository double. Commit its response to an isolated SQLite audit database, then enqueue PlanChecked notification.
2. Write tests first for commit visibility, successful notification, failed/timeout notification, queue saturation, input partitions, response mapping and HTTP flow. Run baseline scaffold to preserve real assertion-failure evidence, not just import errors.
3. Add one bounded asyncio worker and queue; cooperative async transport timeout; bounded metadata event. Do not await transport in request or retry automatically. Keep the primary response stable.
4. Run tests/coverage; inject wrong student_code mapping in a temporary commit, prove the exact-value test fails, then revert it. Review flakiness with isolated DBs and controlled async gates, repeat in reverse order.
5. Run real localhost HTTP with 100 concurrent tasks for small, large accepted, rejected and slow-sender partitions. Publish branch README and evidence; no merge.

Planned files: tools/vt094/{__init__.py,app.py,load.py}; test/test_vt094_notifications.py; docs/tasks/VT-094/*; docs/prompts/VT-094/*.

## Review of plan using repository evidence

- Reject modifying /v1 POST plan-check to save a registration: contract section1 rule6 says read-only, and post_plan_check only computes PlanCheckOut. Use /experiment/plan-check in a standalone harness. SQLite is experimental transaction evidence, NOT production PostgreSQL support.
- Reject sending directly inside a DB transaction (or FastAPI BackgroundTasks alone as a queue limit): a slow/error transport can block transaction/request or create unbounded work. Commit first and use explicit bounded queue/one worker. No real email is sent.
- Reject 500 items as an unexplained domain rule: choose 100 codes of <=32 characters as an experimental resource limit; current PlanCheckBodyIn has no list bound. Reject >100 before repository/SQL work; do not impose that bound on public v1 without team review.
- Reject status-only oracle: compare student_code='T03', university_code='HUS', total_credits=3, max_credits_per_term=24 and exact stored result. This must kill response mapping mutation.

Assumptions: event means completed plan validation (valid or invalid plan), not actual enrolment. Best-effort notification may be dropped on full queue/process death; this change does not promise durable delivery, retry, authentication or real SMTP integration. Async sender must be cancellation-cooperative; blocking synchronous transport is unsupported.
