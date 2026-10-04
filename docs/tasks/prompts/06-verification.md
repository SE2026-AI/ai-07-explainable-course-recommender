# 06 — Independent verification agent

With shared context, act as an independent verifier. Read accepted requirements/contracts before implementation. Do not assume an author's tests prove correctness.

Allowed writes: test/contract/, test/integration/, assigned independent tests, tools/evaluate.*, docs/tasks/VERIFICATION_REPORT.md. Application code is read-only for this assignment; report defects to owners.

Build a representative hand-verifiable evaluation set with no history, missing/failed prerequisites, invalid catalog, no candidates, completed courses, ties, invalid weights, credit boundaries, partial unlocks, unavailable offerings, unchanged baseline and service failure.

Check API fixtures against actual responses and test the complete profile -> recommendations -> why-not -> what-if -> plan flow. Verify score conservation, stable rankings, no unsupported explanation, valid semester ordering, response status and error behavior.

Do not merely duplicate the scoring implementation to compute expected outputs. Use independent calculations, invariants and requirement-derived examples. State test environment, input revision, commands, pass/fail results, missing checks and reproducible defects.

Propose a small user evaluation of explanation comprehension; do not fabricate participants or findings. Separate rule correctness from usefulness of ranking. Synthetic data cannot establish real-world recommendation quality.

Handoff: findings ordered by severity with requirement ID, repro, expected/actual, owner and proposed check. After fixes, rerun affected checks plus needed integration checks; do not declare release readiness with unresolved critical findings.
