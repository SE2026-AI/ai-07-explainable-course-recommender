# Run report — 2026-10-06-mvp-web

## 1. Preflight / assignment envelope (written BEFORE edits)

| Field | Value |
|---|---|
| Ticket / requirement IDs | T-10 Web UI (`docs/tasks/BACKLOG.md`); covers brief items "what-if controls" and "web UI" |
| Task prompt and version | `docs/tasks/prompts/features/10-web.md` v2 (primary); `04-web.md` v2 controls; `common-context.md` v2; `agent-execution-review-protocol.md` v1.0 |
| Human requester / reviewer | ĐinhTruong An (PM/PO, team lead). Reviewer: PENDING |
| Workspace / branch / input commit | `truongan_22001535` @ `163045c`, clean tree |
| Increment / user outcome | Increment 1 (MVP): editable synthetic profile → goals/interests → recommendations with reasons → why-not for blocked courses → what-if weights with before/after |
| Contract | `0.1.0` adopted 2026-10-06. The live backend also exposes `GET /v1/catalog/meta`, a proposed additive endpoint (see the backend run report §5) |
| Inputs / readiness | Backend MVP live via `uvicorn --app-dir src backend.app:app` (READY); contract examples in `docs/architecture/contracts/examples` (READY); reference fixture BASE/FAILED/READY (READY) |
| Exact allowed write files | `src/web/**` (new Vite + React + TypeScript app; the web manifest `src/web/package.json` is owned by this run); `test/web/**`; `docs/tasks/runs/2026-10-06-mvp-web/**`; `docs/tasks/BACKLOG.md` (T-10 status only); `README.md` (run section) |
| Read-only | `src/backend/**`, `docs/architecture/**`, `docs/tasks/prompts/**`, `src/prototype/**` |
| Public output | One typed adapter `src/web/src/api/` with `live` and `mock` implementations; the mock mode is labeled in the UI |
| Out of scope (stretch, per backlog) | semester plan, roadmap, graph UI; clipboard/download |
| Success fixture | BASE (passed CS101 8, MA101 7; goal ML_ENGINEER) → ST201 and SE201 listed as eligible; AI301 shown as blocked by ST201; DL401 blocked via ST201 → AI301 |
| Failure / boundary fixtures | invalid profile (grade 11) → field error shown, no results; API unreachable or 503 → "unavailable" banner, draft kept; injected `ranking_failure` → degraded banner; fast weight changes → only the latest response is shown |
| Given/When/Then (to verify) | AC-1 Given BASE, when recommendations load, then AI301 is in "Chưa đủ điều kiện" with reason ST201 and has no add/score control. AC-2 Given results, when the goal weight is changed, then a before/after comparison from `/v1/simulations` is shown and the baseline list is unchanged. AC-3 Given grade 11, then a field error is shown. AC-4 Given two in-flight requests, when the older one resolves last, then it is ignored. AC-5 Given mock mode, then a visible "MOCK" label is shown. AC-6 Given an API failure, then the profile draft is unchanged and the status is visible |
| Verification commands | `npm test` (Vitest + Testing Library, jsdom) in `src/web`; `npm run build` (tsc + vite); manual browser check against the live backend |
| Evidence path | this folder |
| Assumptions (routine, reversible) | UI language Vietnamese; web dev server on `http://localhost:5173` with `/v1` proxied to `:8000`; weight sliders send raw weights and the backend normalizes them |
| Material decisions needed | none for MVP |
| External actions authorized | push to `truongan_22001535` (prior instruction) |

---

**Task status:** DONE for the T-10 MVP scope in §1. Plan, roadmap and graph were out of scope.
**Review status:** SELF_REVIEWED / INDEPENDENT_REVIEW_PENDING.
**Integration status:** LIVE_VERIFIED locally (Chrome headless → Vite proxy → FastAPI). There is no deployment.

## 2. Change map (final file state)

| Req | Path | Symbol | Line | Before → after | Consumers |
|---|---|---|---|---|---|
| T-10 | `src/web/package.json`, `vite.config.ts`, `tsconfig.json`, `index.html` | web manifest, dev proxy `/v1` → `:8000`, test config pointing at `test/web` | — | NEW | developers |
| AC-5 | `src/web/src/api/client.ts` | `ApiClient`, `createLiveClient`, `createMockClient`, `ApiError` | 38, 51, 97, 19 | NEW: the only adapter; mock replays responses captured from the backend for BASE and computes nothing | `App` |
| T-10 | `src/web/src/api/fixtures/base.json` | mock data | — | NEW: captured from live backend (`rank-0.1`, `catalog-demo-v1`) | mock client |
| AC-4 | `src/web/src/lib/latest.ts` | `createLatestRunner` | 9 | NEW: aborts the previous request; an older response is delivered as `stale` and ignored | `App` (recommend, simulate, meta) |
| AC-6 | `src/web/src/lib/profile.ts` | `PRESETS`, `loadDraft`, `saveDraft` | 42, 51 | NEW: BASE/FAILED/READY presets; draft stored in localStorage behind try/catch | `App`, `ProfileForm` |
| AC-1..6 | `src/web/src/App.tsx` | `App`, `fieldErrorsOf`, `describe` | 45, 31, 36 | NEW: journey, status banners (error/stale/degraded), what-if effect (lines 103–113) | browser |
| AC-3 | `src/web/src/components/ProfileForm.tsx` | `ProfileForm` | 14 | NEW: editable history, goals, interests, workload; field errors next to fields | `App` |
| AC-1 | `src/web/src/components/Results.tsx` | `EligibleCard`, `BlockedCard`, `Breakdown` | 37, 64, 11 | NEW: rank, score, value × weight = contribution, reasons; blocked courses have no score | `App` |
| AC-2 | `src/web/src/components/WhatIf.tsx` | `WhatIf` | 18 | NEW: sliders, adopt/reset, before → after table, entered/exited | `App` |
| T-10 | `src/web/src/components/WhyNot.tsx` | `WhyNot` | 10 | NEW: why-not for any course, including completed ones | `App` |
| tests | `test/web/setup.ts`, `latest.test.ts`, `app.test.tsx` | — | — | NEW | — |

The backend and the contract were not changed in this run.

## 3. Acceptance evidence

Expected values come from `reference-scenarios.json` (BASE) and the backend contract, not from UI output.

| AC | Check | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|
| AC-1 BASE: AI301 not recommendable | Vitest `AC-1/AC-5…` (mock) and browser `AC-1` (live) | eligible = ST201, SE201; AI301 blocked "ST201" | same | PASS | `evidence/vitest.log`, `evidence/browser-checks.json`, `01-base-results-1280.png` |
| AC-2 what-if before/after, baseline unchanged | browser `AC-2` ×2 (live `/v1/simulations`); Vitest `AC-2/AC-4…` | comparison rows for ST201 and SE201; baseline cards identical | ST201 77.8% → 54.5%, SE201 42.6% → 53.0%; cards identical | PASS | `02-whatif-1280.png` |
| AC-3 field error | browser `AC-3` (live 422); Vitest `AC-3…` | message next to the CS101 grade field, no results | "Điểm CS101: Input should be less than or equal to 10" | PASS | `04-invalid-grade.png` |
| AC-4 latest response wins | Vitest `latest.test.ts` (3 tests), `AC-2/AC-4…` (older resolves last with 90% → only 50% shown) | older ignored | ignored | PASS | `vitest.log` |
| AC-5 mock labeled | Vitest, browser `AC-5` | visible MOCK badge | "MOCK · dữ liệu ghi sẵn…" | PASS | `browser-checks.json` |
| AC-6 API failure keeps draft | browser `AC-6` (injected 503); Vitest `AC-6…` (network error) | status banner; edited grade kept | banner shown; grade kept (8 in browser, 9 in Vitest) | PASS | `06-unavailable.png` |
| Degraded labeled | browser `ERR-1` (injected `ranking_failure`); Vitest | degraded banner with code | RANKING_UNAVAILABLE shown | PASS | `05-degraded.png` |
| Narrow layout | browser `UI-1` at 400 px | no horizontal overflow | 0 px | PASS | `03-narrow-400.png` |
| Keyboard | browser `KBD-1` | primary action reachable with Tab and triggered with Enter | 25 Tabs, Enter submitted | PASS | `browser-checks.json` |
| Plan/roadmap, "exact 6-credit plan" | — | — | — | NOT_APPLICABLE (stretch S-01/S-02, no backend endpoint) | — |
| Screen reader, Firefox/Safari, real mobile | — | — | — | UNRUN (no tools available) | — |

Commands:
- `npm test` in `src/web`: 9 passed, exit 0.
- `npm run build`: tsc and vite build OK.
- Browser check: `node evidence/browser-check.mjs <evidence dir>`, using puppeteer-core 23 installed outside the repo and Chrome headless, against `uvicorn --app-dir src backend.app:app` (with `AI07_ALLOW_FAULTS=1`) plus `npx vite`. 10/10 PASS, exit 0.
- Backend `python -m pytest`: 72 passed, unchanged.

## 4. Defects found during the run

| ID | Observed | Root cause | Fix | Status |
|---|---|---|---|---|
| W-1 | `tsc` failed on `vite.config.ts` (`node:url`, `process`) | Node-only config file included in the browser tsconfig | Removed `vite.config.ts` from `include` | FIXED_VERIFIED (build OK) |
| W-2 | Vitest could not load `test/web/*` | Vite blocks files outside its root; bare imports from `test/web` cannot find `src/web/node_modules` | `server.fs.allow` plus an alias regex for react, react-dom and @testing-library | FIXED_VERIFIED |
| W-3 | 4 UI tests failed with "multiple elements" | Test query matched the CS101 option in several selects | `findAllByText` | FIXED_VERIFIED |
| W-4 | In the first screenshots, the sticky submit bar covered the what-if buttons and the credit field | `position: sticky; bottom: 0` over full-page content | Bar moved below the profile form, no longer sticky | FIXED_VERIFIED (`02-whatif-1280.png`, `03-narrow-400.png`) |
| W-5 | At 400 px, the history-row grade field and × button wrapped badly | Two-column grid at the narrow breakpoint | Course select spans the full row; grade and × share the next row | FIXED_VERIFIED (`03-narrow-400.png`) |
| W-6 | Browser check AC-6 errored | Check script selected `aria-label`, but the field is labeled by `<label>` (test script defect, not product) | Script selector fixed | FIXED_VERIFIED |

## 5. Assumptions and limitations

- The UI uses `GET /v1/catalog/meta`, which is still a contract proposal (backend run §5). Every other call uses contract 0.1.0 fields.
- Mock mode always returns BASE results whatever the input. The badge says so.
- The fault-injection selector only has an effect when the backend runs with `AI07_ALLOW_FAULTS=1`.
- The draft is saved in localStorage, per browser only. Nothing is sent anywhere else.

## 6. Run instructions and next step

```bash
# terminal 1 (repo root)
AI07_ALLOW_FAULTS=1 uvicorn --app-dir src backend.app:app --port 8000
# terminal 2
cd src/web && npm install && npm run dev      # http://localhost:5173
```

Next: an independent review of both MVP runs (INDEPENDENT_REVIEW_PENDING). Then T-13 fairness and T-14 ML baseline (required by the brief), or the contract test in `test/contract/`.
