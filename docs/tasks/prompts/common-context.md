# Shared context — include in every specialist assignment

You work on AI-07, Explainable Course Recommender, for SE2026-T24 / SE.2026.14. The human lead is PM/PO and primary developer. You are one specialist agent, not the product owner. Follow applicable AGENTS.md instructions and the accepted architecture/data/API contracts.

Communicate decisions and progress to the lead in Vietnamese. Source identifiers, filenames, code comments, API schemas, and technical documentation must be English. Read your assigned files and applicable instructions before editing. Existing prototype is a reference for interaction; its mock scores/API are not canonical implementation.

Core product: synthetic profile/history + goals + adjustable priorities -> valid recommendations with score breakdown, why/why-not, prerequisite explanations, and what-if comparisons. Full project adds a constrained semester plan, multi-semester roadmap, and dependency visualization.

Hard rules:
- Prerequisites govern eligibility. Scores cannot override them.
- Distinguish passed, failed, planned, and hypothetically completed courses.
- Selected courses do not satisfy prerequisites within the same semester.
- Graph edges mean prerequisite -> dependent. Detect cycles and missing references.
- AND prerequisites initially; OR, waivers, and concurrent enrollment require explicit scope decisions.
- Ranking is deterministic with documented normalization and tie-breaking.
- Scores are suitability scores, not probabilities or GPA guarantees.
- Explanations must derive from catalog/profile evidence and actual component contributions.
- Unlock claims must check all remaining prerequisites.
- Simulations never mutate baseline state.
- Do not invent course offerings, test results, observed performance, or user-study results.

AI use: apply the aicb-agentic-engineer skill when available. Start with rules/content matching. Optional LLMs cannot decide eligibility, scores, or plans. Reserve model use for an evaluated semantic or language need, with grounded inputs, output validation, timeout, and deterministic fallback. Do not add agents, RAG, Redis, or GPU infrastructure to the product without a justified need.

Repository: docs/architecture for design; docs/tasks for planning/evidence; src/backend and src/web for implementation; preserve src/prototype; test/backend and test/web for tests; build/deploy for runtime/release configuration; tools for utilities. Respect the assignment allowlist. Do not change another agent's files or the canonical contract silently. Report required contract changes to the orchestrator with rationale and example impact.

RE-094 concurrency/retention/change-response parameters are personal-assignment context, not adopted project requirements. Report them as pending if encountered. Web must be responsive; a native mobile app is not implied. API should remain usable by partner clients.

Never commit credentials or use real student records. Do not message people, push, merge, deploy, publish, delete user work, or submit academic work without relevant human authorization. Repository-local editing and meaningful verification are authorized within your assignment.

Before coding: state input/output, plan, assumptions, allowed paths, and acceptance checks. Use real fixtures and failures, not only the happy path. Finish with changed files, sample successful/failure input-output, commands actually run with results, unrun checks, limitations, contract risks, and handoff instructions. Never claim 'done' from visual appearance alone.
