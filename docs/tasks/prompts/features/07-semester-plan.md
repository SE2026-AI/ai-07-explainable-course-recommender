# Semester plan feature
Read common-context.md and ranking/eligibility interfaces. Implement a deterministic credit-constrained plan and user selections.
Allowed writes: src/backend/domain/planning*, test/backend/test_planning*. Do not change scoring/graph.
Allow eligible uncompleted courses only. Reject duplicates and credit overflow. Respect exclusions and accepted workload constraints. Record selected courses as planned, not passed. Use a documented heuristic for suggested selection and report unmet preferences/no feasible plan. Never claim global optimality.
Acceptance: exact credit limit works; one-credit overflow fails; duplicate/ineligible selection fails; a selected prerequisite does not enable a dependent in this semester; exclusions are respected; empty eligible set has a clear result. Handoff plan schema examples and actual checks.
