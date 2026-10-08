// Draft profile helpers: presets from docs/tasks/prompts/fixtures/reference-scenarios.json and safe local storage.

import type { Profile, Weights } from "../api/types";

export const DEFAULT_WEIGHTS: Weights = {
  goal_match: 0.5,
  interest_match: 0.2,
  preparation: 0.1,
  workload_fit: 0.2,
};

const common = {
  career_goal_ids: ["ML_ENGINEER"],
  interest_ids: ["DATA"],
  workload_preference: {
    hours_per_week_budget: 12,
    direction: "lower" as const,
  },
  excluded_course_ids: [],
};

export const PRESETS: Record<"BASE" | "FAILED" | "READY", Profile> = {
  BASE: {
    ...common,
    profile_id: "SYN-BASE",
    max_credits_per_term: 6,
    history: [
      { course_id: "CS101", state: "passed", grade: 8 },
      { course_id: "MA101", state: "passed", grade: 7 },
    ],
  },
  FAILED: {
    ...common,
    profile_id: "SYN-FAILED",
    max_credits_per_term: 6,
    history: [
      { course_id: "CS101", state: "passed", grade: 8 },
      { course_id: "MA101", state: "failed", grade: 4 },
    ],
  },
  READY: {
    ...common,
    profile_id: "SYN-READY",
    max_credits_per_term: 8,
    history: [
      { course_id: "CS101", state: "passed", grade: 8 },
      { course_id: "MA101", state: "passed", grade: 7 },
      { course_id: "ST201", state: "passed", grade: 6 },
    ],
  },
};

const KEY = "ai07.draft.v1";

export interface Draft {
  catalogVersion: string;
  profile: Profile;
  weights: Weights;
}

// Storage can be unavailable (private mode, blocked site data); the app must work without it.
export function loadDraft(): Draft | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const draft = JSON.parse(raw) as Draft;
    const p = draft?.profile;
    if (
      !p ||
      typeof p.profile_id !== "string" ||
      !Array.isArray(p.history) ||
      !Array.isArray(p.career_goal_ids) ||
      !Array.isArray(p.interest_ids) ||
      !p.workload_preference ||
      !Number.isFinite(p.workload_preference.hours_per_week_budget) ||
      !Number.isFinite(p.max_credits_per_term)
    )
      return null;
    return draft;
  } catch {
    return null;
  }
}

export function saveDraft(draft: Draft): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(draft));
  } catch {
    /* ignore */
  }
}

export function sameJson(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}
