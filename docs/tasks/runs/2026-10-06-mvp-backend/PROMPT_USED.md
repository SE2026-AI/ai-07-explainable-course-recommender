# Prompt used — run 2026-10-06-mvp-backend

Tool: Claude Code (VS Code extension), model Claude Opus 5.5 (`claude-opus-5-5`). Single agent session; no sub-agents were spawned.

## Human prompts in this session (verbatim, in order)

Off-topic wording was removed and marked `[…]`; nothing was added.

1. *(with a screenshot of the instructor's Classroom post about GitHub repo setup)* `https://github.com/SE2026-AI/ai-07-explainable-course-recommender làm theo thầy t yêu cầu đi`
2. `t đang muốn thử m thôi mà làm thử đi, hoặc cần quyền j để auto`
3. `thêm đi` *(with the permission-rule snippet the agent had suggested)*
4. `brainstorm 18 AI-07 AI Explainable Course Recommender Gợi ý môn học từ mục tiêu và lịch sử giả lập, đồng thời giải thích các điều kiện tiên quyết và cho phép người dùng điều chỉnh ưu tiên. Catalog; profile; ranking; prerequisite validation; explanation; what-if controls. Python/Node; rules + recommender; web UI Trung bình 2 3–5 sinh viên Synthetic data; ranking tests; fairness checks; ADR rules vs ML. xem hiện kiến trúc và các task ổn chưa, lưu ý cấu trúc foder phải tuân theo cấu trúc này do thầy yêu cầu`
5. `có làm đi , còn thành viên […] điền sau`
6. `https://github.com/SE2026-AI/ai-07-explainable-course-recommender/tree/truongan_22001535 push lên đây là dc còn cứ làm đi t là nhóm trưởng ko cần quan tâm bọn còn lại […]`
7. *(mid-run)* `làm mvp thôi đừng làm hết vội, và cũng như đọc 1 vài prompt vì thầy chấm prompt`

## Repository prompts the agent read and applied

| File | How it was used |
|---|---|
| `docs/tasks/prompts/common-context.md` (v2) | Hard invariants, path controls, handoff format |
| `docs/tasks/prompts/agent-execution-review-protocol.md` (v1.0) | Report layout (this folder), change map, acceptance matrix, status vocabulary |
| `docs/tasks/prompts/00-orchestrator.md` (v2) | MVP = increment 1 (catalog/profile/eligibility/ranking/explanation/API/web); Gate B |
| `docs/tasks/prompts/assignment-template.md` (v2) | Envelope filled in `REPORT.md` §1 |
| `docs/tasks/prompts/features/04-ranking.md` (v2) | Ranking boundaries: all-zero/negative/NaN/Inf weights, ties, reference oracle .86/.58 and .44/.82 |
| `docs/tasks/prompts/fixtures/reference-scenarios.json` | BASE/FAILED/READY oracle, used for tests and the demo catalog |

**Read late, important for grading:** the repository prompts were read in detail only after prompt 7. The backend code was written before that, from the architecture docs, which the earlier architecture run had derived from these same prompts. The envelope in `REPORT.md` was therefore filled in **retrospectively**. It is not a preflight made before editing.

## Meaningful AI output excerpts

- Review of the architecture against the brief (after prompt 4): *"So với đề bài thì còn thiếu 2 phần thầy ghi rõ là fairness checks và ADR rules vs ML, và chưa có danh sách task thật để chia việc."* → led to `ADR-001`, `FAIRNESS.md`, `BACKLOG.md` (commit `dacb096`).
- Decision recorded after prompt 6: the team lead adopted the fixture policy as synthetic project policy (T-00). See `docs/architecture/DECISIONS.md` "Adoption record (T-00)".
