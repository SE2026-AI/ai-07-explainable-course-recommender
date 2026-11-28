import { ApiError } from "../errors";
import type { AccountClient } from "./types";

export function createLiveAccountClient(baseUrl = "/v2"): AccountClient {
  const listeners = new Set<() => void>();
  async function call<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    let response: Response;
    try {
      response = await fetch(baseUrl.replace(/\/$/, "") + path, {
        method, credentials: "include", signal,
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch (error) {
      if (signal?.aborted || (error as { name?: string } | null)?.name === "AbortError") throw error;
      throw new ApiError(0, "network_error", "Không kết nối được API.");
    }
    if (response.status === 204) return undefined as T;
    let data: unknown;
    try { data = await response.json(); }
    catch { throw new ApiError(response.status, "bad_response", "API trả về dữ liệu không phải JSON."); }
    if (!response.ok) {
      const error = ApiError.fromBody(response.status, data);
      if (error.code === "unauthenticated") listeners.forEach((notify) => notify());
      throw error;
    }
    return data as T;
  }
  return {
    mode: "live",
    register: (body) => call("POST", "/auth/register", body),
    login: (body) => call("POST", "/auth/login", body),
    logout: () => call("POST", "/auth/logout", {}),
    me: (signal) => call("GET", "/me", undefined, signal),
    password: (body) => call("POST", "/me/password", body),
    deleteAccount: (body) => call("DELETE", "/me", body),
    profile: (body) => call("PUT", "/me/profile", body),
    transcript: (signal) => call("GET", "/me/transcript", undefined, signal),
    saveTranscript: (body) => call("PUT", "/me/transcript", body),
    progress: (signal) => call("GET", "/me/progress", undefined, signal),
    onUnauthenticated: (notify) => { listeners.add(notify); return () => { listeners.delete(notify); }; },
  };
}
