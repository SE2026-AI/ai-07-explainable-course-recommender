import catalog from "./mocks/catalog-response.mock.json";
import graph from "./mocks/graph-response.mock.json";
import success from "./mocks/recommendation-success.mock.json";
import empty from "./mocks/recommendation-empty.mock.json";
import why from "./mocks/why-not.mock.json";
import unavailable from "./mocks/error-unavailable.mock.json";
import type {
  ApiError as ApiErrorBody,
  CatalogPage,
  Graph,
  RecommendationRequest,
  RecommendationResponse,
  WhyNotRequest,
  WhyNotResponse,
} from "./types";
export type ApiMode = "mock" | "live";
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody,
  ) {
    super(body.error.message);
    this.name = "ApiError";
  }
  get code() {
    return this.body.error.code;
  }
  get retryable() {
    return this.body.error.retryable;
  }
  get fieldErrors(): Record<string, string> {
    const errors = this.body.error.details?.errors;
    if (!Array.isArray(errors)) return {};
    return Object.fromEntries(
      errors
        .filter(
          (e): e is { field: string; message: string } =>
            typeof e?.field === "string" && typeof e?.message === "string",
        )
        .map((e) => [e.field, e.message]),
    );
  }
}
export interface ApiClient {
  mode: ApiMode;
  courses(
    version?: string,
    signal?: AbortSignal,
    cursor?: string,
  ): Promise<CatalogPage>;
  graph(version: string, signal?: AbortSignal): Promise<Graph>;
  recommend(
    request: RecommendationRequest,
    signal?: AbortSignal,
  ): Promise<RecommendationResponse>;
  whyNot(request: WhyNotRequest, signal?: AbortSignal): Promise<WhyNotResponse>;
}
export function createLiveClient(baseUrl = "/v1"): ApiClient {
  async function call<T>(
    method: string,
    path: string,
    payload?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
        method,
        signal,
        headers: { "Content-Type": "application/json" },
        body: payload === undefined ? undefined : JSON.stringify(payload),
      });
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") throw error;
      throw new ApiError(0, {
        request_id: "",
        contract_version: "0.1.0",
        error: {
          code: "NETWORK_ERROR",
          message: "Không kết nối được API.",
          retryable: true,
        },
      });
    }
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      throw new ApiError(response.status, {
        request_id: "",
        contract_version: "0.1.0",
        error: {
          code: "BAD_RESPONSE",
          message: "API trả về dữ liệu không phải JSON.",
          retryable: response.status >= 500,
        },
      });
    }
    if (!response.ok) {
      const body = data as Partial<ApiErrorBody> | null;
      throw new ApiError(
        response.status,
        body?.error
          ? (body as ApiErrorBody)
          : {
              request_id: "",
              contract_version: "0.1.0",
              error: {
                code: "HTTP_ERROR",
                message: `HTTP ${response.status}`,
                retryable: response.status >= 500,
              },
            },
      );
    }
    return data as T;
  }
  return {
    mode: "live",
    courses: (version, signal, cursor) => {
      const query = new URLSearchParams({ limit: "100" });
      if (version) query.set("catalog_version", version);
      if (cursor) query.set("cursor", cursor);
      return call("GET", `/catalog/courses?${query}`, undefined, signal);
    },
    graph: (v, s) =>
      call(
        "GET",
        `/catalog/graph?catalog_version=${encodeURIComponent(v)}`,
        undefined,
        s,
      ),
    recommend: (r, s) => call("POST", "/recommendations", r, s),
    whyNot: (r, s) => call("POST", "/why-not", r, s),
  };
}
export type MockScenario = "success" | "empty" | "unavailable";
export function createMockClient(
  scenario: MockScenario = "success",
): ApiClient {
  async function replay<T>(data: T, signal?: AbortSignal): Promise<T> {
    signal?.throwIfAborted();
    if (scenario === "unavailable") throw new ApiError(503, unavailable);
    return structuredClone(data);
  }
  return {
    mode: "mock",
    courses: (_v, s) => replay(catalog, s),
    graph: (_v, s) => replay(graph, s),
    recommend: (_r, s) =>
      replay(
        (scenario === "empty" ? empty : success) as RecommendationResponse,
        s,
      ),
    whyNot: (r, s) =>
      replay(
        {
          ...why,
          results: why.results.filter((row) =>
            r.course_ids.includes(row.course_id),
          ),
        },
        s,
      ),
  };
}
export function createApiClient(): ApiClient {
  return import.meta.env.VITE_API_MODE === "live"
    ? createLiveClient(import.meta.env.VITE_API_BASE_URL || "/v1")
    : createMockClient();
}
