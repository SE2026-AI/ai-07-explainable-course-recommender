export const CONTRACT_VERSION = "0.1.0";
export type HistoryState = "passed" | "failed" | "planned";
export type Direction = "lower" | "higher" | "neutral";
export type ComponentName =
  | "goal_match"
  | "interest_match"
  | "preparation"
  | "workload_fit";
export const COMPONENTS: ComponentName[] = [
  "goal_match",
  "interest_match",
  "preparation",
  "workload_fit",
];
export type Weights = Record<ComponentName, number>;
export interface HistoryRecord {
  course_id: string;
  state: HistoryState;
  grade?: number | null;
  completed_term?: string | null;
  source_record_id?: string | null;
}
export interface Profile {
  profile_id: string;
  history: HistoryRecord[];
  career_goal_ids: string[];
  interest_ids: string[];
  workload_preference: { hours_per_week_budget: number; direction: Direction };
  max_credits_per_term: number;
  excluded_course_ids?: string[];
}
export interface EvidenceRef {
  source: string;
  record_id: string;
}
export interface Reason {
  code: string;
  text: string;
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
  rank: number | null;
  score: number | null;
  contributions?: Partial<Weights>;
  reason_codes: string[];
  evidence_refs?: EvidenceRef[];
  title?: string;
  credits?: number;
  workload_hours_per_week?: number | null;
  score_percent?: number | null;
  components?: Partial<Record<ComponentName, ComponentScore>>;
  reasons?: Reason[];
}
export interface IneligibleCourse {
  course_id: string;
  direct_missing_prerequisite_ids: string[];
  reason_codes: string[];
  title?: string;
  credits?: number;
  transitive_missing_paths?: string[][];
  evidence_refs?: EvidenceRef[];
  reasons?: Reason[];
}
export interface RecommendationRequest {
  contract_version: string;
  catalog_version: string;
  request_id?: string;
  profile: Profile;
  weights?: Weights;
  term_id?: string;
  include_ineligible?: boolean;
}
export interface RecommendationResponse {
  request_id: string;
  contract_version: string;
  catalog_version: string;
  algorithm_version: string;
  status: "ok" | "empty" | "degraded";
  eligible: EligibleCourse[];
  ineligible: IneligibleCourse[];
  warnings?: { code: string; message: string }[];
}
export interface WhyNotRequest {
  contract_version: string;
  catalog_version: string;
  request_id?: string;
  profile: Profile;
  course_ids: string[];
  weights?: Weights;
}
export interface WhyNotResult {
  course_id: string;
  eligible: boolean;
  direct_missing_prerequisite_ids: string[];
  transitive_missing_paths: string[][];
  reason_codes: string[];
  evidence_refs?: EvidenceRef[];
  reasons?: Reason[];
  rank?: number | null;
  score_percent?: number | null;
}
export interface WhyNotResponse {
  request_id: string;
  catalog_version: string;
  results: WhyNotResult[];
}
export interface CatalogCourse {
  course_id: string;
  title: string;
  credits: number;
  workload_hours_per_week?: number | null;
  mandatory_prerequisites: string[];
  recommended_preparation?: string[];
  available_terms: string[];
}
export interface CatalogPage {
  request_id: string;
  contract_version: string;
  catalog_version: string;
  items: CatalogCourse[];
  next_cursor?: string | null;
}
export interface Graph {
  request_id: string;
  catalog_version: string;
  nodes: string[];
  edges: { prerequisite_course_id: string; dependent_course_id: string }[];
}
export interface ApiError {
  request_id: string;
  contract_version: string;
  error: {
    code: string;
    message: string;
    retryable: boolean;
    details?: Record<string, unknown>;
  };
}
// Local form options; the adopted contract does not define a metadata endpoint.
export interface CatalogMeta {
  catalog_version: string;
  goals: { goal_id: string; title: string }[];
  topics: string[];
  terms: string[];
}
