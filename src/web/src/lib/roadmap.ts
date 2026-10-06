// DEMO multi-term roadmap computed in the browser from catalog prerequisite data.
// There is no roadmap API yet (feature 08); replace this with the backend call once it exists.
// It only orders courses by mandatory prerequisites and credit limits; it does not score or recommend.

import type { CatalogCourse, HistoryRecord } from "../api/types";

export interface RoadmapTerm {
  term_id: string;
  course_ids: string[];
  credits: number;
  hours: number;
}

export interface RoadmapResult {
  status: "complete" | "partial";
  terms: RoadmapTerm[];
  /** Courses that are needed but could not be placed within the horizon. */
  unscheduled: string[];
  /** Prerequisites pulled in because a target needs them: course -> the courses that need it. */
  requiredBy: Record<string, string[]>;
}

const TERM_ORDER: Record<string, number> = { SPRING: 0, SUMMER: 1, FALL: 2 };

/** Sort "2027-FALL" style term ids chronologically. */
export function sortTerms(terms: string[]): string[] {
  const key = (t: string) => {
    const [y, s] = t.split("-");
    return Number(y) * 10 + (TERM_ORDER[s] ?? 5);
  };
  return [...terms].sort((a, b) => key(a) - key(b));
}

export function passedIds(history: HistoryRecord[]): Set<string> {
  return new Set(history.filter((h) => h.state === "passed").map((h) => h.course_id));
}

export function planRoadmap(opts: {
  courses: CatalogCourse[];
  history: HistoryRecord[];
  targets: string[];
  horizon: string[];
  maxCreditsPerTerm: number;
}): RoadmapResult {
  const byId = new Map(opts.courses.map((c) => [c.course_id, c]));
  const done = passedIds(opts.history);

  // Close the target set over missing mandatory prerequisites.
  const needed = new Set<string>();
  const requiredBy: Record<string, string[]> = {};
  const visit = (id: string, parent?: string) => {
    if (done.has(id) || !byId.has(id)) return;
    if (parent && !opts.targets.includes(id)) {
      const list = (requiredBy[id] ??= []);
      if (!list.includes(parent)) list.push(parent);
    }
    if (needed.has(id)) return;
    needed.add(id);
    for (const p of byId.get(id)!.mandatory_prerequisites) visit(p, id);
  };
  opts.targets.forEach((t) => visit(t));

  // Depth = longest chain of still-missing prerequisites; schedule shallow (foundational) courses first.
  const depthMemo = new Map<string, number>();
  const depth = (id: string): number => {
    if (depthMemo.has(id)) return depthMemo.get(id)!;
    const pre = byId.get(id)!.mandatory_prerequisites.filter((p) => needed.has(p));
    const d = pre.length ? 1 + Math.max(...pre.map(depth)) : 0;
    depthMemo.set(id, d);
    return d;
  };
  const order = [...needed].sort((a, b) => depth(a) - depth(b) || a.localeCompare(b));

  const completed = new Set(done);
  const terms: RoadmapTerm[] = [];
  for (const term_id of opts.horizon) {
    const placed: string[] = [];
    let credits = 0;
    let hours = 0;
    for (const id of order) {
      if (completed.has(id)) continue;
      const c = byId.get(id)!;
      const offered = !c.available_terms || c.available_terms.length === 0 || c.available_terms.includes(term_id);
      const ready = c.mandatory_prerequisites.every((p) => completed.has(p));
      if (!offered || !ready || credits + c.credits > opts.maxCreditsPerTerm) continue;
      placed.push(id);
      credits += c.credits;
      hours += c.workload_hours_per_week ?? 0;
    }
    placed.forEach((id) => completed.add(id)); // available from the next term on
    terms.push({ term_id, course_ids: placed, credits, hours });
  }
  const unscheduled = order.filter((id) => !completed.has(id));
  return { status: unscheduled.length ? "partial" : "complete", terms, unscheduled, requiredBy };
}
