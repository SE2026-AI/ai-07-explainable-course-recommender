# Run report — 2026-10-06-web-redesign (verification of the T-10 visual redesign)

**Task status:** DONE. The redesign was verified and one defect was fixed.
**Review status:** SELF_REVIEWED / INDEPENDENT_REVIEW_PENDING.
**Integration status:** LIVE_VERIFIED locally (Chrome headless → Vite proxy → FastAPI).

## 1. What happened and who did what

| Step | Actor | Evidence |
|---|---|---|
| Visual redesign of `src/web`: Be Vietnam Pro/Lora fonts, 3-column layout, stacked score bar, prerequisite path chips, why-not chips, what-if rank badges | Human (ĐinhTruong An) | commit `82736b4 giao_dien_fe` |
| Verification, defect fix, evidence | Claude Code agent (Claude Opus 5.5), this session | this report |

Human prompts to the agent (verbatim):
- `chạy lại xem t vừa design lại fe` ("run it again, I just redesigned the FE")
- `check`
- `oke cứ làm theo b, cần làm gì cứ làm` ("ok, do as you suggested, do whatever is needed")

Applied prompt: `docs/tasks/prompts/features/10-web.md` v2, verification and acceptance sections. Contract `0.1.0`. The backend was not changed.

## 2. Checks on the final state

| Check | Result | Evidence |
|---|---|---|
| Test change in `82736b4` (`getByText` → `getAllByText` for ST201 in the AI301 card) | Accepted. ST201 now appears in both the reason and the path chip; the assertion still requires it | `git diff 728aede 82736b4 -- test/web/app.test.tsx` |
| `npm test` | 10 passed (9 existing + 1 new) | `evidence/vitest.log` |
| `npm run build` | OK | — |
| Browser AC-1…AC-6, degraded, 400 px, keyboard | 10/10 PASS | `evidence/browser-checks.json`, `01…06-*.png` |
| Why-not chips (AI301 blocked, CS101 completed, SE201 rank 2) | PASS | `evidence/whynot-browser.log` |
| Backend `python -m pytest` | 72 passed (unchanged) | — |

**Browser-check change, stated openly:** AC-2 "baseline unchanged during what-if" used to compare the full card text. The redesign intentionally adds what-if badges ("giữ hạng", "kịch bản 54.5%") to the baseline cards, so that comparison failed. The check now compares card order, baseline rank and baseline score (`ST201|1|77.8% ; SE201|2|42.6%`), which is what the criterion means. Script: `evidence/browser-check.mjs`.

## 3. Defect fixed in this run

| ID | Observed | Root cause | Fix | Status |
|---|---|---|---|---|
| R-1 | Why-not for a completed course (CS101) said "Chưa thể học ngay" ("cannot take yet") | `WhyNot.tsx` used only `eligible` and ignored the `COMPLETED` reason code | Shows "Đã hoàn thành" when `reason_codes` contains `COMPLETED`; new Vitest `why-not distinguishes completed, blocked and eligible courses` | FIXED_VERIFIED (Vitest and browser) |

## 4. Housekeeping

- 4 identical screenshots (same MD5) had been pasted into `docs/tasks/prompts/features/image/01-catalog/`, which is the read-only prompt folder. Nothing referenced them, so they were removed.

## 5. Limitations

- Fonts load from Google Fonts. Offline, the UI falls back to system fonts and stays usable.
- No screen-reader, Firefox/Safari or real-device testing.
