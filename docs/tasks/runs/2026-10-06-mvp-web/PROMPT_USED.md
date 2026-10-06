# Prompt used — run 2026-10-06-mvp-web

Tool: Claude Code (VS Code extension), model Claude Opus 5.5 (`claude-opus-5-5`). Single agent session, the same session as `2026-10-06-mvp-backend`; no sub-agents were spawned.

## Human prompt (verbatim)

`ừ làm fe cho t test` ("ok, build the frontend so I can test it"). This was a reply to the agent's offer to build web MVP T-10.

Standing instructions from earlier in the session that still applied:
- `làm mvp thôi đừng làm hết vội` ("MVP only, don't build everything yet")
- `đọc 1 vài prompt vì thầy chấm prompt` ("read some of the prompts, because the instructor grades the prompts")

## Repository prompts read BEFORE any edit in this run

| File | Applied as |
|---|---|
| `docs/tasks/prompts/features/10-web.md` v2 | Primary task prompt. Followed: one typed adapter, explicit mock/live toggle, no client-side scoring engine, latest-request-wins, loading/empty/validation/degraded/unavailable states, draft kept on failure, keyboard and narrow/wide layouts |
| `docs/tasks/prompts/04-web.md` v2 | Controls: "no UI placeholder presented as live calculation", "stale scenario results cannot win races", "do not edit backend or contracts" |
| `common-context.md` v2, `agent-execution-review-protocol.md` v1.0, `assignment-template.md` v2 | Envelope (REPORT §1 was written before code), change map, acceptance matrix, status vocabulary |

## Departures from the prompt, stated openly

- The prompt's "plan/roadmap" journey step and the "exact 6-credit plan" acceptance were not implemented. They are stretch items S-01/S-02 in the backlog, and the human asked for MVP only.
- `GET /v1/catalog/meta` is used even though it is still a contract proposal. This is recorded in REPORT §5.

## Meaningful AI output excerpt

Self-review of the first browser screenshots (before the fix): *"Thanh nút 'Gợi ý môn học' đang dính cố định ở đáy màn hình, nên che mất các nút 'Dùng làm gốc/Hoàn tác' (khổ rộng) và ô 'Tín chỉ tối đa' (khổ hẹp)."* → defects W-4 and W-5, fixed and re-verified with new screenshots.
