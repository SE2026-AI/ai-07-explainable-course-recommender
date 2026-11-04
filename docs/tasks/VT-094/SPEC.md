# BT3 VT-094 - reviewed specification

Student: Dinh Truong An / 22001535 / SE2026-T24 / member. Baseline main: 2cbda6b3ebb203b8be1dd664ab60564311be922e (2026-10-26), fetched 2026-11-04. Working branch: truongan_22001535_bt3_vt094.

Problem: after a simulated student finishes checking a term plan, an operator needs a PlanChecked notification, but an unavailable/slow transport must not roll back or hold the completed check. Large inputs must be bounded before expensive domain work.

The current v1 contract is read-only and has no persistent business write or notification transport. This individual assignment uses its expressly allowed executable-harness fallback. Endpoint /experiment/plan-check is a standalone app; it reuses real post_plan_check, check_plan and explanation code, uses SyntheticRepo for 100 generated courses, and commits its response to separate SQLite audit storage. This is not production PostgreSQL integration, enrolment, email delivery, or a v1 change.

## Acceptance criteria (fixed before feature patch)

- AC1: Given HUS/T03 with [C000], when POST /experiment/plan-check succeeds, then HTTP200 has exact HUS/T03/20261, total_credits3, max_credits_per_term24, valid true and violations []; an independently readable audit row equals the response before notification begins.
- AC2: After a committed valid or invalid business plan check, send one small PlanChecked event per request when queue capacity exists. Unknown course and duplicate course are completed invalid plans (HTTP200/valid false). Event contains event/check_id/valid/course_count, not the full course list or sensitive data.
- AC3: Sender error, cooperative timeout or full queue cannot change/delete committed result or main HTTP response. Sending uses one worker, bounded queue128, timeout50ms/attempt, no retry; full queue drops with observable counter. No durable-delivery promise.
- AC4: Input has 1..100 string codes of length1..32 and forbids extra fields. Empty, >100, oversized code, null/non-list type fail HTTP422 before domain/SQL work. Main computation/commit failure produces error and no notification.
- AC5: Under 100 concurrent HTTP tasks, measure end-to-end latency against p95<=3.0s for small and largest accepted input, invalid oversized input, and slow sender. Count wrong response or lost audit rows as failure. Publish all outcomes and measurement limits, even when target fails.

NFC1: queue and per-event metadata bounded; not more than one in-flight send; no unbounded asyncio tasks. NFC2: public v1 remains byte/schema compatible, no new auth/secrets/packages for transport. NFC3: notification timeout50ms only bounds cancellation-cooperative async senders; synchronous/blocking or cancellation-resistant implementations are unsupported. NFC4: SQLite is local experimental storage; disk errors/locks are primary failures, not notification failures.

Invariant: notification is offered ONLY after a successful commit; failed main work never sends. Transport availability cannot modify main result. Delivery after process death, dedup/retry, SMTP/provider contract and authentication are outside this slice.

## Test strategy / equivalence partitioning

Unit: queue saturation/counters; small deterministic resource-bound tests. Integration/API: FastAPI validation, actual rules/API assembly and SQLite commit visibility across two connections, controlled sender double. Executable E2E: actual loopback HTTP -> validation -> real domain -> SQLite -> async sender, exercised by tools/vt094/load.py. Browser/mobile/SMTP E2E is unnecessary for this isolated backend harness (no UI/provider changed); production E2E and PostgreSQL persistence remain unproven.

Equivalence classes: list cardinality invalid0 / valid1..100 / invalid>100; code length invalid0 / valid1..32 / invalid>32; shape list strings / wrong list or item type; business known / unknown / duplicate; transport success / raises / hangs / saturated; primary commits / fails. Representative data independent of implementation constants: 0,1,100,101,10000 entries; 32/33-char codes. Boundaries supplement, not replace, equivalence partitioning.

| ID | Requirement/risk | Level | Precondition/input | Expected | Priority |
|---|---|---|---|---|---|
| T01 | AC1/AC2 wrong mapping/order | API+SQLite | HUS/T03,[C000], recording sender | exact fields; committed row visible to sender; one event | P0 |
| T02 | AC3 transport failure | API+SQLite | sender raises OSError |200;row remains;failed1 | P0 |
| T03 | AC3 timeout | API+worker | sender waits on Event forever, timeout10ms test config |200;row remains;failed1;queue drains | P0 |
| T04 | AC4 invalid partitions | API | empty,101 codes,code33,null item,non-list |422;0 rows | P0 |
| T05 | AC4 large-input failure path | API |10000 codes + repository that raises if called |422;repository never called;0 rows | P0 |
| T06 | AC2 business invalid | API+domain |UNKNOWN / C000 twice |200/valid false;expected violation;event valid false | P1 |
| T07 | AC2/4 max accepted | API+domain |100 distinct known codes |total300,max24;small event count100 | P0 |
| T08 | AC3/4 primary commit fails | API+storage |save raises OperationalError |500;no event;0 rows | P0 |
| T09 | AC3 queue resource | Unit |queue1;offer2 before worker starts |first true,second false;size1;dropped1 | P0 |
| T10 | AC4 extra input | API |send_to extra field |422;0 rows | P1 |
| T11 | AC4 main lookup error | API+domain |no student program |404;no event;0 rows | P0 |
| T12 | AC4 code length valid class | API+domain |32-char unknown code |200/not_in_curriculum | P1 |
| T13 | shared state flake | API+storage |two apps with different tmp_path DBs |each first id1;no cross-test rows | P1 |
| T14 | AC3 saturation isolation | API+worker |in-flight gated sender,queue1,three requests |all200/three commits;one dropped | P0 |
| T15 | AC4 lower invalid code | API |empty string code |422;0 rows | P1 |
| L01-04 | AC5 timeout/performance | HTTP E2E/load |100 workers;small,100 codes,10000 rejected,slow sender |p95<=3s or explicit fail;correctness and row counts | P0 |

No test result is preclaimed here. Red/green, mutation, coverage and load logs record actual runs separately. No other student artefacts are reused.
