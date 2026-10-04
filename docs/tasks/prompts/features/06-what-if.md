# What-if comparison feature
Read common-context.md and stable ranking/profile contracts. Implement isolated scenario changes and baseline comparison through the canonical engine.
Allowed writes: src/backend/domain/simulation*, test/backend/test_simulation*. UI/API owners consume your interface.
Support accepted changes to goal, weights, credit/workload preferences, course exclusions and explicitly hypothetical completions. Preserve baseline inputs/results. Define rank changes for a common eligible candidate set, and report newly eligible/ineligible courses separately. Include explanation changes, reproducibility/version metadata and validation errors.
Acceptance: original profile remains unchanged; the same scenario reproduces output; adjusted priorities change designed fixture rankings; invalid input is rejected; hypothetical completion stays simulated; reset returns the baseline. Handoff before/after fixture and integration notes. Do not implement a separate ranking formula.
