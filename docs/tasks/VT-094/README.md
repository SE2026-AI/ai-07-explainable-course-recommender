# Individual assignment BT3 - VT-094 / 22001535

**Branch:** https://github.com/SE2026-AI/ai-07-explainable-course-recommender/tree/truongan_22001535_bt3_vt094

Baseline main: `2cbda6b3ebb203b8be1dd664ab60564311be922e`.
Student: Dinh Truong An, member SE2026-T24. No merge or group approval is claimed.

## Scope

Standalone synthetic-only executable harness for the permitted fallback, not a production-v1 change.
Business event: `PlanChecked`. Real project `post_plan_check`, rules and explanation run over a synthetic Repository double.
The main experimental transaction commits its output to SQLite, then offers a bounded metadata event to one async worker.
Queue128, timeout50ms, best-effort/no retries. A failed/slow sender or full queue does not undo the main commit.
Process exit may lose notifications. Blocking/cancellation-resistant transport is unsupported. No real message is sent.

No change to `src/`, PostgreSQL data, OpenAPI or public API v1. A real deployment needs a team-approved write contract, PostgreSQL adapter and transport integration. The 100-code limit is experimental, not a new domain rule for v1.

## Run from repository root (Python >=3.11)

```text
python -m pip install -r requirements.txt
python -c "from pathlib import Path; Path('.vt094-tmp').mkdir(exist_ok=True)"
python -m pytest test/test_vt094_notifications.py -q --basetemp=.vt094-tmp/check --cov=tools.vt094.app --cov-branch
python -m tools.vt094.verify
python -m tools.vt094.load
python -m ruff check tools/vt094 test/test_vt094_notifications.py
```

No PostgreSQL or SMTP account required. Test databases are isolated files. Windows temp permissions required explicit basetemp in this environment. Test output includes one existing Starlette deprecation warning.

## Evidence / sequence

- `d88412b`: reviewed plan + executable characterization scaffold; no notification implementation.
- `d9bb48d`: tests and genuine red log,14 failed/6 passed before notification patch.
- `2a65151`: small feature patch;20 passed, coverage recorded. Initial resource warnings exposed a SQLite connection lifetime issue; `closing()` fixed it before this accepted green result.
- Temporary branch `truongan_22001535_bt3_mutation`: mutation commit `3539c220a201a3a9931aadad67ec51f1d54a2b83`, changes response student_code to university_code. T01 fails exact-value assertion. It is NOT merged into submission branch; mutation.diff and03_mutation_killed.txt preserve evidence.
- `evidence/04_repeat_*`: three complete runs, reverse/normal/reverse,20 pass each; no retry-to-pass.
- `evidence/05_regression.txt`:117 existing pure-logic tests pass,one PostgreSQL-dependent case deselected.
- `evidence/load-results.json`, `load-requests.csv`, `06_load_run.txt`: actual HTTP100 workers x3 attempts per phase; all attempts counted; audit deltas verified; see results for unmet performance targets. Short local experiment is not production capacity proof.
- `evidence/coverage.json`: line/branch details for new harness only. Missing invalid internal configuration branch is disclosed; high line coverage alone does not establish correctness.

Specification and >=10 cases: `SPEC.md`. AI prompts/review: `docs/prompts/VT-094/`. Reflection: `REFLECTION.md`.
Mutation reproduction: inspect `evidence/mutation.diff`, apply the one-line change to a separate temporary branch, run T01, restore correct code and rerun full slice tests. Do not apply mutation to submitted branch.

## Review of generated patch

Scope: only tools/test/assignment docs. Design: commit precedes enqueue; one bounded worker. Correctness: sender exceptions are caught only in worker; primary errors propagate to existing error handler; SQL parameterized; SQLite connections closed explicitly; no destination/credential accepted. Evidence: red then green, mapping mutation, queue gates, reverse-order repeats and actual HTTP load.

Unproven: PostgreSQL/provider/browser integration, durable delivery, incoming raw-body byte limit, cancellation-resistant sender and long soak/race behavior. SQLite lock failures under load are primary storage failures; do not mislabel them notification rollback. No independent teammate review is claimed.
