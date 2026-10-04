# Synthetic profile and goals feature
Read common-context.md and assignment. Implement editable synthetic academic history, goals, interests and preferences using canonical schemas.
Allowed writes: assigned src/backend/domain/profile*, goals*, src/backend/data/profiles*, goals*, test/backend/test_profile*, test_goals*. Shared models and API transport need named ownership.
Distinguish passed, failed, planned and hypothetical records. Validate grades, course IDs, interest ranges, credit limits and goal identifiers according to accepted policies. Define empty-history behavior. Changes to simulation data must not update the baseline profile. Use synthetic IDs only.
Acceptance: valid edits round-trip; invalid grade/course/credit input produces a field-level contract error; failed courses do not satisfy prerequisites; changing goal changes subsequent recommendation input; no history remains a supported state. Handoff fixtures and expected outputs for eligibility/web agents.
