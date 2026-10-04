# Why/why-not explanation feature
Read common-context.md and ranking/eligibility outputs. Implement structured explanations derived from evidence and actual contributions.
Allowed writes: src/backend/domain/explanation*, test/backend/test_explanation*. Read ranking/graph only.
Return reason codes, readable reasons, warnings, score breakdown and source record references. Distinguish ineligible, completed, eligible-but-low-ranked and excluded-from-plan. Name prerequisites and conditional unlocks correctly. Missing evidence cannot support a claim. Use deterministic templates initially; do not add an LLM just for phrasing.
Acceptance: score explanation equals actual contributions; missing prerequisite appears in why-not; changing priorities changes the relevant explanation; multiple prerequisites prevent false unlock claims; missing evidence yields an honest omission/error according to contract. Handoff successful and rejected-course explanations and tests.
