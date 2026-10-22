// Tầng gọi API v1. Đường dẫn và kiểu lấy từ docs/api/openapi.json (src/api/types.ts, sinh tự động).
// Hiện có 8 endpoint đang chạy thật; endpoint sinh viên (§6.4–6.7) và prerequisite-graph được
// thêm vào đây khi issue API tương ứng merge và openapi.json có chúng.
import { ApiError } from "./errors";
import { mockClient, type MockScenario } from "./mock";
import type {
  CurriculumCourses,
  CurriculumDetail,
  CurriculumSummary,
  DataIssues,
  Health,
  Meta,
  Term,
  University,
} from "./schema";

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
}

/** Ghép đường dẫn, mã hóa từng mã tự nhiên trong path. */
function path(strings: TemplateStringsArray, ...codes: string[]): string {
  return strings.reduce((out, s, i) => out + s + (i < codes.length ? encodeURIComponent(codes[i]) : ""), "");
}

export function createLiveClient(baseUrl = "/v1"): ApiClient {
  const root = baseUrl.replace(/\/$/, "");

  async function get<T>(route: string, signal?: AbortSignal): Promise<T> {
    let response: Response;
    try {
      response = await fetch(root + route, { headers: { Accept: "application/json" }, signal });
    } catch (error) {
      if (signal?.aborted || (error as { name?: unknown })?.name === "AbortError") throw error;
      throw new ApiError(0, "network_error", "Không kết nối được API.");
    }
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw new ApiError(response.status, "bad_response", "API trả về dữ liệu không phải JSON.");
    }
    if (!response.ok) throw ApiError.fromBody(response.status, body);
    // §9.5: trường lạ được giữ nguyên và bỏ qua, không kiểm tra chặt để không vỡ khi API thêm trường.
    return body as T;
  }

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
