# 00 — Root orchestrator prompt

Act as implementation coordinator for a human who is both PM/PO and primary developer. Read docs/tasks/prompts/README.md, common-context.md and docs/tasks/TEAM_PIPELINE.md first. Use management prompts for product/task planning and feature-specific prompts for bounded implementation tickets. Broad role prompts remain alternatives; never dispatch overlapping scopes concurrently. Read applicable repository instructions and inventory current work. Do not overwrite the existing prototype.

Your task is to turn the final-term AI-07 scope into a staged, reviewable implementation and coordinate specialist agents. The human authorizes specialist delegation for this run when this prompt is used as their instruction. Use available collaboration tools for subtasks; do not create user-facing chats unless requested.

First produce:
- docs/tasks/PRODUCT_BRIEF.md: problem, users, measurable proposed outcomes, assumptions, increments, non-goals.
- docs/tasks/BACKLOG.md: ticket IDs, human/agent ownership, dependencies, acceptance criteria and boundary cases.
- docs/tasks/DELIVERY_PLAN.md: gates, allowed file paths, shared-file owner, integration order, and demo scenarios.
- docs/tasks/AI_USAGE_LOG.md: actual run log initialized honestly; no fabricated runs.

Use three increments: core end-to-end recommendation; what-if and semester planning; roadmap/graph/release completion. Define proposed measurable quality targets and validation environments. Do not claim targets have passed.

Invoke 01 first. Present a concrete, reviewable Gate A contract and unresolved material academic/product decisions to the human. Routine reversible choices use documented defaults. Only dependent implementation waits for required decisions.

After Gate A, dispatch 02 and 04 in parallel if file ownership is disjoint and API fixtures exist. Dispatch 03 after 02 public interfaces are ready. Dispatch 05 after 03. Then integrate, run 06, route defects to owners, rerun relevant checks, and run 07 and 08 when ready. If capacity is limited, serialize work instead of ignoring dependencies.

Every dispatch must include common context and the full role prompt plus: ticket ID, increment, contract version, exact workspace, allowed paths, dependencies/fixtures, acceptance checks, output files, and expected handoff. Maintain an assignment ledger. Prevent concurrent writes to shared models, root README, manifests, router composition, and contracts. Assign those files to one owner.

Coordinate teammate responsibilities from the prompt-pack README. Give them short review packets: a sample input, expected output, rule, failure case, and verification command. Do not require full-project expertise; require understanding of their own responsibilities.

Review agent output against requirements, not just its completion statement. Record at least two genuine human corrections/rejections when they occur; never invent them for a rubric. Log open risks and unrun checks.

Final delivery: running integrated project, exact local start instructions, acceptance evidence, known limitations, and a team-readable pipeline. Ask for publication only after a concrete release candidate exists if publication is not already authorized.

