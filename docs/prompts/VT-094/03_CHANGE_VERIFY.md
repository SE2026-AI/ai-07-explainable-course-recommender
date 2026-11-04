# Prompt P3 - implement only after red evidence

Inputs: reviewed 01_PLAN.md, SPEC.md, red commit d9bb48d, evidence/01_red.txt:14 failed/6 passed. Implement only tools/vt094/app.py; no src/v1/database changes.

Add Input constraints (1..100 codes,1..32 characters,extra forbid), one bounded asyncio Queue worker, cancellation-cooperative send timeout, counters sent/failed/dropped. Audit commit must finish before queue offer; on queue full keep primary response/commit. Event metadata bounded and no full plan payload. Default sender is local no-op only. Do not install provider packages or send a real message. Explain limitation that in-memory best-effort delivery loses events on shutdown/crash.

Preserve actual post_plan_check output and SQLite parameterized insert. Run red tests unchanged; inspect diff before committing. Then measure line/branch coverage, repeated reversed-order runs; mutate student_code mapping in temporary commit, run T01 to prove kill and revert. Keep raw logs and Git hash references. Actual HTTP load uses100 tasks and p95<=3s, report failures honestly.

## Output used / review checklist

Patch: bounded Notifier, Input constraints, lifespan worker, offer after threadpool primary returns committed audit id/result. No new dependency, no public-v1 change.
Review gates: scope only standalone harness; async exception isolation cannot catch primary errors; wait_for only cancels cooperative transports; sqlite save context commits before return; exact response/student_code assertions are independent; queue-full counter explicit. A single worker plus finite queue limits outstanding sends, not maximum incoming HTTP body bytes.
