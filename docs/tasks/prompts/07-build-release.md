# 07 — Build and release preparation agent

With shared context and a verified integrated increment, prepare reproducible local execution and release configuration.

Allowed writes: build/deploy/, assigned package/dependency manifests, .env.example, root README.md, tools/run.*, approved CI exception at .github/workflows/. Manifest ownership must be assigned before editing. Do not change product logic.

Document supported runtime versions, dependencies, data initialization, backend/frontend commands, ports, health checks, and test commands. Use compatible locked dependencies where practical. Include environment-variable examples without secrets. Avoid promising version support that has not been tested.

Prepare containers only when useful for reproducibility and explain relative build contexts from build/deploy. CI runs contract/domain/integration checks and frontend build appropriate to implemented scope. Do not add production infrastructure without a deployment requirement.

Perform a clean-start rehearsal in an isolated temporary environment where available. Record actual commands and results. If unavailable, mark clean-start unverified and document the limitation.

Write a demo/release checklist and recovery steps. No push, publication, cloud deployment or external account action is authorized by this preparation assignment.

Handoff: exact startup instructions, environment requirements, successful checks, known setup limitations and a release candidate for human acceptance.
