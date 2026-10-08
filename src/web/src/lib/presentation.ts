import type * as Api from "../api/types";
export type { ComponentName } from "../api/types";
export type EligibleCourse = Api.EligibleCourse & {
  title: string;
  credits: number;
  workload_hours_per_week: number | null;
  score_percent: number | null;
  reasons: Api.Reason[];
  components: Record<Api.ComponentName, Api.ComponentScore>;
};
export type IneligibleCourse = Api.IneligibleCourse & {
  title: string;
  credits: number;
  transitive_missing_paths: string[][];
  reasons: Api.Reason[];
};
export type RecommendationResponse = Omit<
  Api.RecommendationResponse,
  "eligible" | "ineligible" | "warnings"
> & {
  eligible: EligibleCourse[];
  ineligible: IneligibleCourse[];
  warnings: NonNullable<Api.RecommendationResponse["warnings"]>;
};
export type WhyNotResult = Api.WhyNotResult & { reasons: Api.Reason[] };
const labels: Record<string, string> = {
  GOAL_MATCH: "Phù hợp mục tiêu nghề nghiệp",
  MISSING_PREREQUISITE: "Thiếu môn tiên quyết",
  COMPLETED: "Đã hoàn thành",
};
function reasons(row: {
  reasons?: Api.Reason[];
  reason_codes: string[];
  evidence_refs?: Api.EvidenceRef[];
}): Api.Reason[] {
  return (
    row.reasons ??
    row.reason_codes.map((code) => ({
      code,
      text: labels[code] ?? code,
      evidence_refs: row.evidence_refs ?? [],
    }))
  );
}
export function explainView(row: Api.WhyNotResult): WhyNotResult {
  return { ...row, reasons: reasons(row) };
}
export function resultsView(
  data: Api.RecommendationResponse,
  courses: Api.CatalogCourse[],
): RecommendationResponse {
  const lookup = (id: string) => courses.find((c) => c.course_id === id);
  return {
    ...data,
    warnings: data.warnings ?? [],
    eligible: data.eligible.map((row) => ({
      ...row,
      title: row.title ?? lookup(row.course_id)?.title ?? row.course_id,
      credits: row.credits ?? lookup(row.course_id)?.credits ?? 0,
      workload_hours_per_week:
        row.workload_hours_per_week ??
        lookup(row.course_id)?.workload_hours_per_week ??
        null,
      score_percent:
        row.score_percent ??
        (row.score == null ? null : Math.round(row.score * 1000) / 10),
      reasons: reasons(row),
      components: Object.fromEntries(
        ApiComponents.map((name) => [
          name,
          row.components?.[name] ?? {
            value: null,
            weight: 0,
            effective_weight: 0,
            contribution: row.contributions?.[name] ?? 0,
            available: row.contributions?.[name] != null,
          },
        ]),
      ) as Record<Api.ComponentName, Api.ComponentScore>,
    })),
    ineligible: data.ineligible.map((row) => ({
      ...row,
      title: row.title ?? lookup(row.course_id)?.title ?? row.course_id,
      credits: row.credits ?? lookup(row.course_id)?.credits ?? 0,
      transitive_missing_paths: row.transitive_missing_paths ?? [],
      reasons: reasons(row),
    })),
  };
}
import { COMPONENTS as ApiComponents } from "../api/types";
