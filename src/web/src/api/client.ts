// Tầng gọi API v1. Đường dẫn và kiểu lấy từ docs/api/openapi.json (src/api/types.ts, sinh tự động).
// Đủ 14 endpoint của §6.
import { ApiError } from "./errors";
import { mockClient, type MockScenario } from "./mock";
import type {
  CourseStatus,
  CurriculumCourses,
  CurriculumDetail,
  CurriculumSummary,
  DataIssues,
  Health,
  Meta,
  PlanCheck,
  PlanCheckBody,
  PrerequisiteGraph,
  RecommendationBody,
  Recommendations,
  StudentProfile,
  Term,
  University,
} from "./schema";

/** Một sinh viên được định danh bằng cặp mã trường + mã sinh viên (§1.3). */
export interface StudentRef {
  uni: string;
  student: string;
}

/** Tham số `term` của mọi endpoint sinh viên; vắng thì server dùng học kỳ mặc định (§3.1). */
export interface TermQuery {
  term?: string;
}

export type ApiMode = "mock" | "live";

export interface ApiClient {
  readonly mode: ApiMode;
  health(signal?: AbortSignal): Promise<Health>;
  meta(signal?: AbortSignal): Promise<Meta>;
  universities(signal?: AbortSignal): Promise<University[]>;
  terms(uni: string, signal?: AbortSignal): Promise<Term[]>;
  curricula(uni: string, signal?: AbortSignal): Promise<CurriculumSummary[]>;
  curriculum(uni: string, curriculumCode: string, signal?: AbortSignal): Promise<CurriculumDetail>;
  curriculumCourses(
    uni: string,
    curriculumCode: string,
    signal?: AbortSignal,
  ): Promise<CurriculumCourses>;
  dataIssues(signal?: AbortSignal): Promise<DataIssues>;
  prerequisiteGraph(uni: string, curriculumCode: string, signal?: AbortSignal): Promise<PrerequisiteGraph>;
  profile(ref: StudentRef, query?: TermQuery, signal?: AbortSignal): Promise<StudentProfile>;
  courseStatus(ref: StudentRef, query?: TermQuery, signal?: AbortSignal): Promise<CourseStatus>;
  /** GET: trọng số mặc định, không giả định. */
  recommendations(
    ref: StudentRef,
    query?: TermQuery & { limit?: number },
    signal?: AbortSignal,
  ): Promise<Recommendations>;
  /** POST: trọng số tùy chọn và what-if (`assumptions`, `skip`, `swap`). */
  recommend(ref: StudentRef, body: RecommendationBody, signal?: AbortSignal): Promise<Recommendations>;
  planCheck(ref: StudentRef, body: PlanCheckBody, signal?: AbortSignal): Promise<PlanCheck>;
}

/** Ghép đường dẫn, mã hóa từng mã tự nhiên trong path. */
function path(strings: TemplateStringsArray, ...codes: string[]): string {
  return strings.reduce((out, s, i) => out + s + (i < codes.length ? encodeURIComponent(codes[i]) : ""), "");
}

/** Query string từ các tham số có giá trị; rỗng thì không thêm "?". */
function query(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") q.set(k, String(v));
  const text = q.toString();
  return text ? `?${text}` : "";
}

const studentPath = ({ uni, student }: StudentRef) => path`/universities/${uni}/students/${student}`;

export function createLiveClient(baseUrl = "/v1"): ApiClient {
  const root = baseUrl.replace(/\/$/, "");

  async function call<T>(method: "GET" | "POST", route: string, body: unknown, signal?: AbortSignal): Promise<T> {
    let response: Response;
    try {
      response = await fetch(
        root + route,
        method === "GET"
          ? { headers: { Accept: "application/json" }, signal }
          : {
              method,
              headers: { Accept: "application/json", "Content-Type": "application/json" },
              body: JSON.stringify(body),
              signal,
            },
      );
    } catch (error) {
      if (signal?.aborted || (error as { name?: unknown })?.name === "AbortError") throw error;
      throw new ApiError(0, "network_error", "Không kết nối được API.");
    }
    let parsed: unknown;
    try {
      parsed = await response.json();
    } catch {
      throw new ApiError(response.status, "bad_response", "API trả về dữ liệu không phải JSON.");
    }
    if (!response.ok) throw ApiError.fromBody(response.status, parsed);
    // §9.5: trường lạ được giữ nguyên và bỏ qua, không kiểm tra chặt để không vỡ khi API thêm trường.
    return parsed as T;
  }
  const get = <T,>(route: string, signal?: AbortSignal) => call<T>("GET", route, undefined, signal);
  const post = <T,>(route: string, body: unknown, signal?: AbortSignal) => call<T>("POST", route, body, signal);

  return {
    mode: "live",
    health: (s) => get("/health", s),
    meta: (s) => get("/meta", s),
    universities: (s) => get("/universities", s),
    terms: (uni, s) => get(path`/universities/${uni}/terms`, s),
    curricula: (uni, s) => get(path`/universities/${uni}/curricula`, s),
    curriculum: (uni, code, s) => get(path`/universities/${uni}/curricula/${code}`, s),
    curriculumCourses: (uni, code, s) => get(path`/universities/${uni}/curricula/${code}/courses`, s),
    dataIssues: (s) => get("/data-issues", s),
    prerequisiteGraph: (uni, code, s) => get(path`/universities/${uni}/curricula/${code}/prerequisite-graph`, s),
    profile: (ref, q = {}, s) => get(`${studentPath(ref)}/profile${query({ term: q.term })}`, s),
    courseStatus: (ref, q = {}, s) => get(`${studentPath(ref)}/course-status${query({ term: q.term })}`, s),
    recommendations: (ref, q = {}, s) =>
      get(`${studentPath(ref)}/recommendations${query({ term: q.term, limit: q.limit })}`, s),
    recommend: (ref, body, s) => post(`${studentPath(ref)}/recommendations`, body, s),
    planCheck: (ref, body, s) => post(`${studentPath(ref)}/plan-check`, body, s),
  };
}

export function createMockClient(scenario: MockScenario = "success"): ApiClient {
  return mockClient(scenario);
}

export function createApiClient(env: ImportMetaEnv = import.meta.env): ApiClient {
  return env.VITE_API_MODE === "live"
    ? createLiveClient(env.VITE_API_BASE_URL || "/v1")
    : createMockClient();
}

export { ApiError };
export type { MockScenario };
