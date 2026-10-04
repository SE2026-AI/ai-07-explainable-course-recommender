# Multi-semester roadmap feature
Read common-context.md and prerequisite/planning contracts. Generate a bounded deterministic heuristic roadmap.
Allowed writes: src/backend/domain/roadmap*, test/backend/test_roadmap*, docs/architecture/PLANNING.md.
Only previous-semester completion enables prerequisites. Enforce per-semester credits, completed-course exclusion, offerings and user exclusions. Use declared synthetic offering assumptions when real offerings are absent. Return partial/infeasible status with reasons for unreachable goals, oversized prerequisite, unavailable offering or exhausted horizon. Do not claim optimality or real course availability.
Acceptance: every scheduled prerequisite is completed earlier; credits never overflow; unavailable courses are not scheduled; excluded required course yields clear infeasibility; horizon terminates; identical input reproduces roadmap. Verify hand-constructed two/three-semester examples, including failure. Handoff UI fixtures.
