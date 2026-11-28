import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/errors";
import { createLiveAccountClient } from "../api/v2/client";
import { createMockAccountClient } from "../api/v2/mock";
import { safeReturnTo } from "../lib/account";

afterEach(() => vi.unstubAllGlobals());
const CODE = "HUS-7480113QTD-2022";
const credentials = { email: "mock@example.test", password: "fake-password-only" };
describe("v2 live transport", () => {
  it("all nine endpoint operations include credentials and JSON;204 is not parsed", async () => {
    const fetch = vi.fn().mockImplementation(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetch);
    const api = createLiveAccountClient("/v2/");
    await api.register(credentials); await api.login(credentials); await api.logout(); await api.me();
    await api.password({ current_password: "old-fake", new_password: "new-fake" });
    await api.deleteAccount({ password: "fake-only" }); await api.profile({ curriculum_code: CODE });
    await api.transcript(); await api.saveTranscript({ semesters_completed: 0, results: [] }); await api.progress();
    expect(fetch.mock.calls.map(([url, init]) => [url, init.method])).toEqual([
      ["/v2/auth/register", "POST"], ["/v2/auth/login", "POST"], ["/v2/auth/logout", "POST"], ["/v2/me", "GET"],
      ["/v2/me/password", "POST"], ["/v2/me", "DELETE"], ["/v2/me/profile", "PUT"],
      ["/v2/me/transcript", "GET"], ["/v2/me/transcript", "PUT"], ["/v2/me/progress", "GET"],
    ]);
    for (const [, init] of fetch.mock.calls) {
      expect(init.credentials).toBe("include"); expect(init.headers["Content-Type"]).toBe("application/json");
    }
  });
  it("session expiry notifies;wrong password does not discard a valid session", async () => {
    const fetch = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ error: { code: "unauthenticated", message: "expired", details: {} } }), { status: 401 }));
    vi.stubGlobal("fetch", fetch);
    const api = createLiveAccountClient(); const expired = vi.fn(); const unsubscribe = api.onUnauthenticated(expired);
    await expect(api.transcript()).rejects.toMatchObject({ code: "unauthenticated" }); expect(expired).toHaveBeenCalledOnce();
    fetch.mockResolvedValue(new Response(JSON.stringify({ error: { code: "invalid_credentials", message: "wrong", details: {} } }), { status: 401 }));
    await expect(api.password({ current_password: "wrong-fake", new_password: "new-fake" })).rejects.toMatchObject({ code: "invalid_credentials" });
    expect(expired).toHaveBeenCalledOnce(); unsubscribe();
  });
  it("does not hide abort,network or non-JSON errors", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch); const api = createLiveAccountClient();
    fetch.mockRejectedValue(new TypeError("offline")); await expect(api.me()).rejects.toMatchObject({ code: "network_error" });
    fetch.mockResolvedValue(new Response("gateway", { status: 502 })); await expect(api.me()).rejects.toMatchObject({ code: "bad_response" });
    const abort = new DOMException("aborted", "AbortError"); fetch.mockRejectedValue(abort);
    await expect(api.me()).rejects.toBe(abort);
  });
  it.each(["https://outside.test", "//outside.test", "/\\outside.test", "/dang-nhap?next=/dang-nhap"])("rejects unsafe return path %s", (path) => {
    expect(safeReturnTo(path)).toBe("/cua-toi");
  });
  it("keeps internal path,query and anchor", () => expect(safeReturnTo("/cua-toi?tab=1#row")).toBe("/cua-toi?tab=1#row"));
});
describe("v2 stateful mock boundary", () => {
  it("normalizes email,requires profile,replaces transcript and retains it after logout/login", async () => {
    const api = createMockAccountClient();
    await expect(api.me()).rejects.toMatchObject({ status: 401 });
    await api.register({ ...credentials, email: " MOCK@example.test " });
    expect((await api.me()).user.email).toBe("mock@example.test");
    await expect(api.transcript()).rejects.toMatchObject({ code: "profile_required" });
    await api.profile({ curriculum_code: CODE });
    await api.saveTranscript({ semesters_completed: 2, results: [{ course_code: "MAT2400", semester: 1, score: 7.5 }] });
    await api.logout(); await expect(api.transcript()).rejects.toMatchObject({ status: 401 });
    await api.login(credentials); expect((await api.transcript()).results).toHaveLength(1);
    await api.saveTranscript({ semesters_completed: 2, results: [] }); expect((await api.transcript()).results).toEqual([]);
  });
  it("does not mix two accounts;delete clears account data", async () => {
    const api = createMockAccountClient(); await api.register(credentials); await api.profile({ curriculum_code: CODE });
    await api.saveTranscript({ semesters_completed: 1, results: [{ course_code: "MAT2400", semester: 1, score: 9 }] });
    await api.logout(); await api.register({ ...credentials, email: "second@example.test" });
    expect((await api.me()).profile).toBeNull(); await api.profile({ curriculum_code: CODE });
    expect((await api.transcript()).results).toEqual([]);
    await api.deleteAccount({ password: credentials.password });
    await expect(api.login({ ...credentials, email: "second@example.test" })).rejects.toMatchObject({ code: "invalid_credentials" });
    await api.login(credentials); expect((await api.transcript()).results[0].score).toBe(9);
  });
  it("422 does not change saved data;409 requires explicit clearing before curriculum change", async () => {
    const api = createMockAccountClient(); await api.register(credentials); await api.profile({ curriculum_code: CODE });
    await api.saveTranscript({ semesters_completed: 1, results: [{ course_code: "MAT2400", semester: 1, score: 8 }] });
    await expect(api.saveTranscript({ semesters_completed: 1, results: [{ course_code: "MAT2400", semester: 1, score: 12 }] })).rejects.toBeInstanceOf(ApiError);
    expect((await api.transcript()).results[0].score).toBe(8);
    await expect(api.profile({ curriculum_code: "HUS-7460108-2022" })).rejects.toMatchObject({ code: "transcript_not_empty" });
    await api.saveTranscript({ semesters_completed: 1, results: [] }); await api.profile({ curriculum_code: "HUS-7460108-2022" });
    expect((await api.transcript()).results).toEqual([]);
  });
});
