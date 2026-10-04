# 05 — What-if and roadmap agent

With shared context and stable ranking/prerequisite interfaces, implement isolated simulation and constrained planning.

Allowed paths: src/backend/domain/simulation.*, planning.*, roadmap.*, assigned simulation/roadmap routers, test/backend/test_simulation*, test_planning*, test_roadmap*, docs/architecture/PLANNING.md. Do not alter the scoring engine or graph rules silently.

What-if: clone baseline inputs; apply validated goal, weight, credit, workload, exclusion or hypothetical-completion changes; call the canonical engine. Return comparable score/rank/eligibility changes and reasons. Never persist hypothetical completion into actual history. Define how ranks are compared when eligibility changes.

Semester plan: select only eligible, uncompleted courses within credits using a documented deterministic heuristic. User exclusions must be respected. Report unmet preferences and no-feasible-plan cases.

Roadmap: bounded horizon; previous-semester completions satisfy prerequisites in later semesters only. Respect course availability data or label an explicit synthetic availability assumption. Handle a prerequisite too large for the credit budget, unavailable course, unreachable goal and exhausted horizon. Return partial plan with causes when appropriate; never claim optimality.

Verify immutable baseline, exact credit limit, changing priority, excluded prerequisite, hypothetical completion, same-semester dependency rejection, all-prerequisite unlocks, and infeasible roadmap. Use hand-verifiable data before large synthetic data.

Handoff: before/after JSON example, valid and infeasible roadmap examples, actual test results, heuristic limitations and frontend integration notes.
