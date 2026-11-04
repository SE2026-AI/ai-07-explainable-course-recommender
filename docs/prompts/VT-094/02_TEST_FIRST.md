# Prompt P2 - test first, stop before notification implementation

Context: read 01_PLAN.md and tools/vt094/app.py characterization scaffold. No notifications or request-size bound exist yet. Do not implement them in this step.
Write test/test_vt094_notifications.py. Oracles come from reviewed AC, not production constants: response HUS/T03, 3 credits, max24; SQLite row must already be visible to sender. Input partitions: empty, 1..100 known, unknown, duplicates, >100, oversized/incorrect type; representative boundaries 0/1/100/101 and code length32/33.
Failure tests: sender raises; sender never finishes but cancels; queue full; main commit fails; unknown student. Large input must be rejected before DB work. Test notification worker bounds directly and actual HTTP/SQLite/real plan-check in integration. Use isolated tmp_path and async gates, no random test data, no real email.
Run this test file on the scaffold; save full failure log. Confirm failures are missing notification/validation behavior or expected assertion, not import/environment failures. Commit tests and red evidence before editing app.py.

AI output used: tests in test/test_vt094_notifications.py. Review will inspect exact response assertions and at-commit visibility, not only HTTP200.
