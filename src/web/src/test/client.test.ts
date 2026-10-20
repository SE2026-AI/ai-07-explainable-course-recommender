import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createApiClient, createLiveClient, createMockClient, type ApiClient } from "../api/client";
import meta from "../api/mocks/contract/meta.json";
import curriculum from "../api/mocks/contract/curriculum.json";
import courses from "../api/mocks/contract/curriculum-courses.json";
import dataIssues from "../api/mocks/contract/data-issues.json";
import studentNotFound from "../api/mocks/contract/error-student-not-found.json";
import health from "../api/mocks/seed/health.json";
import universities from "../api/mocks/seed/universities.json";
import terms from "../api/mocks/seed/terms.json";
import curricula from "../api/mocks/seed/curricula.json";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function stubFetch(...responses: Response[]) {
  const fetcher = vi.fn();
  for (const r of responses) fetcher.mockResolvedValueOnce(r);
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}

async function caught(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    return error as ApiError;
  }
  throw new Error("Đáng lẽ phải lỗi");
}

afterEach(() => vi.unstubAllGlobals());

const cases: [string, (c: ApiClient) => Promise<unknown>, string, unknown][] = [
  ["health", (c) => c.health(), "/v1/health", health],
  ["meta", (c) => c.meta(), "/v1/meta", meta],
  ["universities", (c) => c.universities(), "/v1/universities", universities],
  ["terms", (c) => c.terms("HUS"), "/v1/universities/HUS/terms", terms],
  ["curricula", (c) => c.curricula("HUS"), "/v1/universities/HUS/curricula", curricula],
  [
    "curriculum",
    (c) => c.curriculum("HUS", "HUS-7480113QTD-2022"),
    "/v1/universities/HUS/curricula/HUS-7480113QTD-2022",
    curriculum,
  ],
  [
    "curriculumCourses",
    (c) => c.curriculumCourses("HUS", "HUS-7480113QTD-2022"),
    "/v1/universities/HUS/curricula/HUS-7480113QTD-2022/courses",
    courses,
  ],
  ["dataIssues", (c) => c.dataIssues(), "/v1/data-issues", dataIssues],
];

describe("live client: 8 endpoint đang chạy", () => {
  it.each(cases)("%s gọi đúng đường dẫn và parse đúng ví dụ", async (_name, call, url, body) => {
    const fetcher = stubFetch(json(body));
    await expect(call(createLiveClient())).resolves.toEqual(body);
    expect(fetcher).toHaveBeenCalledWith(url, expect.objectContaining({ headers: { Accept: "application/json" } }));
  });

  it("mã hóa mã tự nhiên trong đường dẫn và nhận baseUrl có dấu / cuối", async () => {
    const fetcher = stubFetch(json([]));
    await createLiveClient("http://127.0.0.1:8000/v1/").curricula("A B/C");
    expect(fetcher.mock.calls[0][0]).toBe("http://127.0.0.1:8000/v1/universities/A%20B%2FC/curricula");
  });

  it("§9.5: bỏ qua trường lạ ở mọi tầng của phản hồi", async () => {
    const extra = {
      ...courses,
      next_page: "x",
      courses: courses.courses.map((c) => ({ ...c, new_field: { nested: [1, 2] } })),
    };
    stubFetch(json(extra));
    const result = await createLiveClient().curriculumCourses("HUS", "HUS-7480113QTD-2022");
    expect(result.courses[0].prerequisite_groups).toEqual([["HUS1011"]]);
    expect(result.count).toBe(65);
  });
});

describe("ApiError theo §5", () => {
  it("dựng từ ví dụ lỗi của hợp đồng, details là object, không có request_id", async () => {
    stubFetch(json(studentNotFound, 404));
    const error = await caught(createLiveClient().meta());
    expect(error).toMatchObject({
      status: 404,
      code: "student_not_found",
      message: "Không tìm thấy sinh viên T99 của trường HUS.",
      details: { university_code: "HUS", student_code: "T99" },
      isRoutingError: false,
    });
    expect(error.userMessage).toContain("Không tìm thấy sinh viên");
    expect(error).not.toHaveProperty("request_id");
  });

  it.each([
    [404, "route_not_found", { path: "/v1/nope" }],
    [405, "method_not_allowed", { method: "POST", path: "/v1/meta" }],
    [400, "http_error", {}],
  ])("%i %s là lỗi lập trình, không phải lỗi dữ liệu", async (status, code, details) => {
    stubFetch(json({ error: { code, message: "server", details } }, status));
    const error = await caught(createLiveClient().meta());
    expect(error.isRoutingError).toBe(true);
    expect(error.userMessage).toMatch(/^Lỗi lập trình/);
    expect(error.details).toEqual(details);
  });

  it("422 đọc được details.fields", async () => {
    stubFetch(
      json(
        {
          error: {
            code: "validation_error",
            message: "Dữ liệu gửi lên không hợp lệ.",
            details: { fields: { limit: "Input should be less than or equal to 20" } },
          },
        },
        422,
      ),
    );
    const error = await caught(createLiveClient().meta());
    expect(error.fieldErrors).toEqual({ limit: "Input should be less than or equal to 20" });
  });

  it("mã lạ thì dùng message của server; details thiếu thì thành object rỗng", async () => {
    stubFetch(json({ error: { code: "brand_new_code", message: "Câu của server." } }, 409));
    const error = await caught(createLiveClient().meta());
    expect(error.userMessage).toBe("Câu của server.");
    expect(error.details).toEqual({});
  });

  it("phản hồi lỗi sai định dạng, không phải JSON, hoặc mất mạng", async () => {
    stubFetch(json({ detail: "Not Found" }, 404), new Response("<html>", { status: 502 }));
    expect(await caught(createLiveClient().meta())).toMatchObject({ status: 404, code: "bad_response" });
    expect(await caught(createLiveClient().meta())).toMatchObject({ status: 502, code: "bad_response" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    expect(await caught(createLiveClient().meta())).toMatchObject({ status: 0, code: "network_error" });
  });

  it("hủy request thì ném lại AbortError, không bọc thành ApiError", async () => {
    const abort = new DOMException("aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(createLiveClient().meta()).rejects.toBe(abort);
  });
});

describe("mock client", () => {
  it.each(cases)("%s phát lại đúng fixture", async (_name, call, _url, body) => {
    await expect(call(createMockClient())).resolves.toEqual(body);
  });

  it("trả bản sao, sửa kết quả không làm hỏng lần gọi sau", async () => {
    const api = createMockClient();
    (await api.curriculumCourses("HUS", "x")).courses.length = 0;
    expect((await api.curriculumCourses("HUS", "x")).courses).toHaveLength(1);
  });

  it("kịch bản rỗng", async () => {
    const api = createMockClient("empty");
    expect(await api.universities()).toEqual([]);
    expect(await api.curricula("HUS")).toEqual([]);
    expect(await api.curriculumCourses("HUS", "C")).toEqual({ curriculum_code: "C", count: 0, courses: [] });
    expect(await api.dataIssues()).toEqual({ count: 0, issues: [] });
  });

  it("kịch bản lỗi", async () => {
    const api = createMockClient("error");
    expect(await caught(api.meta())).toMatchObject({ status: 500, code: "internal_error" });
    expect(await caught(api.curricula("XX"))).toMatchObject({
      code: "university_not_found",
      details: { university_code: "XX" },
    });
    expect(await caught(api.curriculum("HUS", "C"))).toMatchObject({ code: "curriculum_not_found" });
  });
});

describe("VITE_API_MODE", () => {
  it("mặc định là mock, live khi đặt live", () => {
    expect(createApiClient({} as ImportMetaEnv).mode).toBe("mock");
    expect(createApiClient({ VITE_API_MODE: "live" } as ImportMetaEnv).mode).toBe("live");
  });
});
