# 04 — Web experience agent

With shared context and accepted API fixtures, implement the web experience. You may start with fixture-backed responses while backend work continues.

Allowed paths: src/web/, test/web/, docs/tasks/WEB_HANDOFF.md. Preserve src/prototype as a reference. Do not implement a second canonical ranking or prerequisite engine in JavaScript. Use API-calculated scores and eligibility.

Deliver incrementally: editable synthetic profile -> goal selection -> recommendations -> explanations -> plan selection. Then add priority controls, baseline/scenario comparison, roadmap and graph once their contracts are ready.

Use one API adapter with explicit mock/live configuration. Label mock mode. Handle loading, empty, field validation, unavailable and degraded states. Request changes should not show an old response as the new scenario; handle rapid priority updates and out-of-order responses. Use validated contracts and fixtures, not guessed fields.

Show suitability scores with contribution breakdown, missing prerequisites, reasons, warnings and evidence. Make completed/ineligible/planned courses visually distinct. Allow why-not exploration. Keep baseline visibly separate from scenario results; provide reset.

Support small and large screens, keyboard use, labels and focus states. Do not claim native mobile implementation. Keep product text understandable and technical diagnostics in the partner/debug view where useful.

Verify core flow, blocked course, exact credit boundary, invalid profile, empty recommendations, rapid scenario changes and API failure. Include meaningful UI checks and actual results. Do not say every browser/device is supported from one screenshot.

Handoff: start command, fixture mode/live mode instructions, screenshots or reproducible review steps, checks run, accessibility/viewport coverage and limitations.
