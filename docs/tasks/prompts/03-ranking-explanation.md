# 03 — Ranking and explanation agent

With shared context, accepted contracts and prerequisite interfaces, implement reproducible recommendations and structured why/why-not explanations.

Allowed paths: src/backend/domain/ranking.*, explanation.*, recommendations.*, assigned API routers/app composition, test/backend/test_ranking*, test_explanation*, test_recommendations*. Do not edit agent 02 domain files or web. Shared application/model ownership must be explicit in your assignment.

Consume catalog/profile and eligibility interfaces. Remove passed courses and separate ineligible candidates from recommendable-now results. Compute normalized components using the canonical definitions and weights. Enforce finite values, valid weight ranges, documented all-zero behavior and stable tie-breaking. Return score contributions that reconcile with the displayed total.

Create structured reasons from actual component contributions and record-level evidence. Explain relevant drawbacks. Distinguish low rank from ineligibility and from exclusion by a plan's credit budget. Explain conditional unlocks precisely. No LLM is required for this increment.

Implement assigned /v1 routes and errors using contract fixtures. Keep HTTP transport separate from domain calculations. Include version/provenance data needed to reproduce results.

Verify: identical requests reproduce rankings; missing prerequisites cannot be offset by goal score; all-zero/invalid weights follow contract; ties are stable; displayed contributions sum correctly; why-not reflects actual cause; optional missing profile data behaves as documented.

Handoff: sample eligible and ineligible responses, verification commands/results, fixtures for web, ready interface for simulation/planning, and any unresolved contract issues.
