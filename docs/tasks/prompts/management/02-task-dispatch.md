# Task decomposition and agent dispatch prompt

Read common-context.md, TEAM_PIPELINE.md, accepted backlog and contracts. Act as delivery coordinator. Allowed writes: docs/tasks/TICKETS.md and ASSIGNMENTS.md. Delegate only when the human run instruction authorizes agent use; preparing tickets does not require spawning agents.

Split backlog into bounded tasks with one outcome and verifiable handoff. For each, fill assignment-template.md, choose one feature/role prompt, list exact file allowlist, prerequisites, fixtures, interface, success/failure criteria and commands. Document source/manifests/router/contract owners to prevent concurrent edits.

Identify genuinely parallel tasks. Mark blocked work by named dependency. Use isolated workspaces when needed and specify integration order. Do not create user-facing chats, GitHub issues, or message teammates unless authorized.

Provide review packets to A/B/C matching TEAM_PIPELINE.md. Include an example input, expected output, rule and failure case. Handoff a runnable dispatch schedule, with planned versus dispatched states clearly separated.
