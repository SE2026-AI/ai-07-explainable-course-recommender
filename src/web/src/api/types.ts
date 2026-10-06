// Types for contract 0.1.0 (docs/architecture/contracts/openapi.yaml) plus the additive fields the backend returns.

export const CONTRACT_VERSION = "0.1.0";

export type HistoryState = "passed" | "failed" | "planned";
export type Direction = "lower" | "higher" | "neutral";
export type ComponentName = "goal_match" | "interest_match" | "preparation" | "workload_fit";
export const COMPONENTS: ComponentName[] = ["goal_match", "interest_match", "preparation", "workload_fit"];
export type Weights = Record<ComponentName, number>;

export interface HistoryRecord {
  course_id: string;
  state: HistoryState;
  grade: number | null;
}

export interface Profile {
  profile_id: string;
  history: HistoryRecord[];
  career_goal_ids: string[];
  interest_ids: string[];
  workload_preference: { hours_per_week_budget: number; direction: Direction };
  max_credits_per_term: number;
  excluded_course_ids: string[];
}

export interface EvidenceRef {
  source: string;
  record_id: string;
}

export interface Reason {
  code: string;
  text: string;
  component?: ComponentName;
  evidence_refs: EvidenceRef[];
}

export interface ComponentScore {
  value: number | null;
  weight: number;
  effective_weight: number;
  contribution: number;
  available: boolean;
}

export interface EligibleCourse {
  course_id: string;
  title: string;
  credits: number;
  workload_hours_per_week: number | null;
  rank: number | null;
  score: number | null;
  score_percent: number | null;
  unlocks: string[];
  components?: Record<ComponentName, ComponentScore>;
  components_missing?: ComponentName[];
  reason_codes: string[];
  reasons: Reason[];
}

export interface IneligibleCourse {
  course_id: string;
  title: string;
  credits: number;
  direct_missing_prerequisite_ids: string[];
  transitive_missing_paths: string[][];
  reason_codes: string[];
  reasons: Reason[];
}

export interface Warning {
  code: string;
  message: string;
  field?: string;
}

export interface RecommendationResponse {
  request_id: string;
  contract_version: string;
  catalog_version: string;
  algorithm_version: string;
  status: "ok" | "empty" | "degraded";
  weights: Weights;
  eligible: EligibleCourse[];
  ineligible: IneligibleCourse[];
  warnings: Warning[];
}

export interface SimulationSide {
  weights: Weights;
  eligible_course_ids: string[];
  scores: Record<string, number | null>;
  ranks: Record<string, number | null>;
}

export interface SimulationResponse {
  request_id: string;
  baseline_version: string;
  scenario_id: string;
  scenario_version: string;
  comparable_candidate_set_id: string;
  baseline: SimulationSide;
  scenario: SimulationSide;
  changes: { course_id: string; rank_before: number | null; rank_after: number | null; score_before: number | null; score_after: number | null; score_delta: number | null }[];
  entered: string[];
  exited: string[];
}

export interface WhyNotResult {
  course_id: string;
  eligible: boolean;
  rank?: number | null;
  score_percent?: number | null;
  direct_missing_prerequisite_ids: string[];
  transitive_missing_paths: string[][];
  reason_codes: string[];
  reasons: Reason[];
}

export interface WhyNotResponse {
  request_id: string;
  catalog_version: string;
  results: WhyNotResult[];
}

export interface CatalogMeta {
  catalog_version: string;
  available_catalog_versions: string[];
  goals: { goal_id: string; title: string }[];
  topics: string[];
  terms: string[];
}

export interface CatalogCourse {
  course_id: string;
  title: string;
  credits: number;
  workload_hours_per_week: number | null;
  mandatory_prerequisites: string[];
}

export interface CatalogPage {
  catalog_version: string;
  items: CatalogCourse[];
  next_cursor: string | null;
}

export interface ApiErrorBody {
  request_id: string;
  contract_version: string;
  error: { code: string; message: string; retryable: boolean; details?: Record<string, unknown> };
}
