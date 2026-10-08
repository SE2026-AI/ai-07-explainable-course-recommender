import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createLiveClient, createMockClient } from "../api/client";
import fixture from "../api/mocks/profile.mock.json";
import { CONTRACT_VERSION, type Profile } from "../api/types";
import { resultsView } from "../lib/presentation";
const request = {
  contract_version: CONTRACT_VERSION,
  catalog_version: fixture.catalog_version,
  profile: fixture.profile as Profile,
};
afterEach(() => vi.unstubAllGlobals());
describe("contract adapter", () => {
  it("joins compact ranking with catalog without changing score contributions", async () => {
    const api = createMockClient();
    const data = await api.recommend(request);
    const courses = await api.courses();
    const view = resultsView(data, courses.items);
    expect(view.eligible[0].title).toBe("Xác suất thống kê");
    expect(view.eligible[0].score_percent).toBe(86);
    expect(
      view.eligible[0].components.goal_match.contribution +
        view.eligible[0].components.workload_fit.contribution,
    ).toBeCloseTo(data.eligible[0].score!);
  });
  it("supports empty and structured outage fixtures", async () => {
    expect((await createMockClient("empty").recommend(request)).status).toBe(
      "empty",
    );
    await expect(
      createMockClient("unavailable").courses(),
    ).rejects.toMatchObject({
      status: 503,
      code: "CATALOG_UNAVAILABLE",
      retryable: true,
    });
  });
  it("filters why-not by requested ID and returns isolated fixtures", async () => {
    const api = createMockClient();
    expect(
      (await api.whyNot({ ...request, course_ids: ["CS101"] })).results,
    ).toEqual([]);
    const one = await api.recommend(request);
    one.eligible.length = 0;
    expect((await api.recommend(request)).eligible).toHaveLength(1);
  });
  it("sends contract requests and cursor parameters to live endpoints", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ results: [] })));
    vi.stubGlobal("fetch", fetcher);
    const api = createLiveClient();
    const payload = { ...request, course_ids: ["AI301"] };
    await api.whyNot(payload);
    expect(fetcher).toHaveBeenCalledWith(
      "/v1/why-not",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      }),
    );
    fetcher.mockResolvedValue(new Response("{}"));
    await api.courses("catalog-demo-v1", undefined, "next page");
    expect(fetcher.mock.calls[1][0]).toContain("cursor=next+page");
  });
  it("preserves 422 field errors and reports malformed/network responses", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            request_id: "req",
            contract_version: "0.1.0",
            error: {
              code: "VALIDATION",
              message: "Bad grade",
              retryable: false,
              details: {
                errors: [{ field: "profile.history.0.grade", message: "0–10" }],
              },
            },
          }),
          { status: 422 },
        ),
      );
    vi.stubGlobal("fetch", fetcher);
    try {
      await createLiveClient().recommend(request);
      throw new Error("expected error");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).fieldErrors).toEqual({
        "profile.history.0.grade": "0–10",
      });
    }
    fetcher.mockResolvedValue(new Response("bad"));
    await expect(createLiveClient().courses()).rejects.toMatchObject({
      code: "BAD_RESPONSE",
    });
    fetcher.mockRejectedValue(new TypeError("offline"));
    await expect(createLiveClient().courses()).rejects.toMatchObject({
      code: "NETWORK_ERROR",
      status: 0,
    });
  });
});
