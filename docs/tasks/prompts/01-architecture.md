# 01 — Architecture and canonical contract agent

With the shared context, act as a software architect and requirements engineer. Produce designs and fixtures first; do not implement application services yet.

Allowed outputs: docs/architecture/ARCHITECTURE.md, DATA_MODEL.md, API.md, RECOMMENDER_DESIGN.md, DECISIONS.md, contracts/openapi.yaml, contracts/examples/*.json. Propose the source layout and interface ownership without moving existing files.

Inspect repository constraints. Recommend one concrete modular stack, defaulting to Python/FastAPI backend and React/TypeScript web when no established stack exists. Explain why each dependency is needed. Describe how source, tests, runtime configuration and utilities map to existing root folders.

Specify course, profile, goal, preference, eligibility, recommendation, explanation, what-if and roadmap schemas. Define passed-course policy, unknown/missing fields, units for workload, score ranges, unavailable offerings, AND prerequisites, and graph orientation. Unconfirmed policies must be visibly proposed assumptions.

Version API at /v1. Cover catalog/profile reads or edits, recommendations, why-not, simulations and roadmap. Define request validation, errors, request IDs, response states, and fixture bodies for successful, empty, invalid and degraded/unavailable cases. Recommend stateless simulation requests unless persistence has a defined user need.

Define shared backend interfaces between prerequisite, ranking, explanation and planning modules. Name owners of models, app entrypoint, API routers, package manifests, and fixtures. A frontend-ready fixture must include score breakdown, missing prerequisites, conditional unlocks and provenance.

Unify scoring components and weights across API, algorithm and UI. State normalization, all-zero-weight behavior, deterministic ties, evidence generation, and baseline comparison semantics. Specify eligible ranking separately from ineligible why-not results.

Create Given/When/Then acceptance cases and proposed correctness thresholds. Include cycle, missing reference, no eligible courses, invalid weights, credit boundary and unavailable roadmap cases. Use no invented measurements.

Handoff: design files, contract version, complete sample request/response, unresolved decisions requiring human input, and interface checklist for agents 02–05. Gate A is reviewed by the human lead; you cannot self-approve it.
