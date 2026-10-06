// The single typed API adapter. `live` calls the backend; `mock` replays responses captured from the backend.
// Neither computes eligibility or scores: the backend is the only recommender.

import fixtures from "./fixtures/base.json";
import {
  CONTRACT_VERSION,
  type ApiErrorBody,
  type CatalogMeta,
  type CatalogPage,
  type Profile,
  type RecommendationResponse,
  type SimulationResponse,
  type Weights,
  type WhyNotResponse,
} from "./types";

export type ApiMode = "live" | "mock";

export class ApiError extends Error {
  constructor(
    public readonly status: number, // 0 = network failure
    public readonly code: string,
    message: string,
    public readonly retryable: boolean,
    public readonly details?: Record<string, unknown>,
    public readonly requestId?: string,
  ) {
    super(message);
  }

  /** Field-level errors from 422 responses, keyed by dotted field path. */
  get fieldErrors(): Record<string, string> {
    const list = (this.details?.errors as { field: string; message: string }[] | undefined) ?? [];
    return Object.fromEntries(list.map((e) => [e.field, e.message]));
  }
}

export interface ApiClient {
  mode: ApiMode;
  meta(catalogVersion?: string, signal?: AbortSignal): Promise<CatalogMeta>;
  courses(catalogVersion: string, signal?: AbortSignal): Promise<CatalogPage>;
  recommend(catalogVersion: string, profile: Profile, weights: Weights, signal?: AbortSignal): Promise<RecommendationResponse>;
  simulate(catalogVersion: string, profile: Profile, baselineWeights: Weights, scenarioWeights: Weights, scenarioId: string, signal?: AbortSignal): Promise<SimulationResponse>;
  whyNot(catalogVersion: string, profile: Profile, courseIds: string[], weights: Weights, signal?: AbortSignal): Promise<WhyNotResponse>;
}

function body(catalogVersion: string, profile: Profile) {
  return { contract_version: CONTRACT_VERSION, catalog_version: catalogVersion, profile };
}

export function createLiveClient(baseUrl = "/v1", faultHeader?: string): ApiClient {
  async function call<T>(method: "GET" | "POST", path: string, payload?: unknown, signal?: AbortSignal): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method,
        signal,
        headers: { "Content-Type": "application/json", ...(faultHeader ? { "X-AI07-Fault": faultHeader } : {}) },
        body: payload === undefined ? undefined : JSON.stringify(payload),
      });
    } catch (err) {
      if ((err as Error).name === "AbortError") throw err;
      throw new ApiError(0, "NETWORK_ERROR", "Không kết nối được tới API.", true);
    }
    const text = await response.text();
    let data: unknown;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      throw new ApiError(response.status, "BAD_RESPONSE", "API trả về dữ liệu không phải JSON.", response.status >= 500);
    }
    if (!response.ok) {
      const err = (data as ApiErrorBody | null)?.error;
      throw new ApiError(response.status, err?.code ?? "HTTP_ERROR", err?.message ?? `HTTP ${response.status}`, err?.retryable ?? response.status >= 500,
        err?.details, (data as ApiErrorBody | null)?.request_id);
    }
    return data as T;
  }

  return {
    mode: "live",
    meta: (v, signal) => call("GET", `/catalog/meta${v ? `?catalog_version=${encodeURIComponent(v)}` : ""}`, undefined, signal),
    courses: (v, signal) => call("GET", `/catalog/courses?catalog_version=${encodeURIComponent(v)}&limit=100`, undefined, signal),
    recommend: (v, profile, weights, signal) => call("POST", "/recommendations", { ...body(v, profile), weights }, signal),
    simulate: (v, profile, baselineWeights, scenarioWeights, scenarioId, signal) =>
      call("POST", "/simulations", {
        ...body(v, profile),
        baseline_version: "ui-baseline",
        weights: baselineWeights,
        scenario: { scenario_id: scenarioId, scenario_version: "1", weights: scenarioWeights },
      }, signal),
    whyNot: (v, profile, courseIds, weights, signal) => call("POST", "/why-not", { ...body(v, profile), course_ids: courseIds, weights }, signal),
  };
}

/** Replays BASE-profile responses captured from the backend. Inputs are ignored; the UI labels this mode MOCK. */
export function createMockClient(delayMs = 150): ApiClient {
  const wait = <T,>(value: T): Promise<T> => new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), delayMs));
  const data = fixtures as unknown as {
    meta: CatalogMeta; courses: CatalogPage; recommendations: RecommendationResponse; simulation: SimulationResponse; whyNot: WhyNotResponse;
  };
  return {
    mode: "mock",
    meta: () => wait(data.meta),
    courses: () => wait(data.courses),
    recommend: () => wait(data.recommendations),
    simulate: () => wait(data.simulation),
    whyNot: (_v, _p, ids) => wait({ ...data.whyNot, results: data.whyNot.results.filter((r) => ids.includes(r.course_id)) }),
  };
}
