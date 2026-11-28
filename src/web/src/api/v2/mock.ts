import { ApiError } from "../errors";
import baseProgress from "../mocks/contract/transcript.json";
import curricula from "../mocks/seed/curricula.json";
import examples from "./examples.json";
import type { AccountClient, Profile, Progress, SavedTranscript, Session, User } from "./types";

// Mock transport only: no real credentials, cookies or transcripts are persisted in the browser.
// Login simulates a session; it deliberately does not implement password verification in JavaScript.
export function createMockAccountClient(): AccountClient {
  type Account = { user: User; profile: Profile | null; transcript: SavedTranscript | null };
  const users = new Map<string, Account>();
  const listeners = new Set<() => void>();
  let current: Account | null = null;
  const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));
  const now = () => new Date().toISOString();
  const fail = (status: number, code: string, fields?: Record<string, string>): never => {
    throw new ApiError(status, code, code, fields ? { fields } : {});
  };
  function account(): Account {
    if (!current) { listeners.forEach((notify) => notify()); fail(401, "unauthenticated"); }
    return current!;
  }
  function selected(): Account & { profile: Profile } {
    const a = account();
    if (!a.profile) fail(409, "profile_required");
    return a as Account & { profile: Profile };
  }
  function checkPassword(password: string, field = "password") {
    if (password.length < 8 || password.length > 128) fail(422, "validation_error", { [field]: "Mật khẩu dài 8–128 ký tự." });
  }
  function credentials(email: string, password: string): string {
    checkPassword(password);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) fail(422, "validation_error", { email: "Email không hợp lệ." });
    return email.trim().toLowerCase();
  }
  return {
    mode: "mock",
    async register(body) {
      const email = credentials(body.email, body.password);
      if (users.has(email)) fail(409, "email_taken");
      const sample = examples["6.1"][1].user as User;
      current = { user: { ...sample, user_id: crypto.randomUUID(), email, created_at: now() }, profile: null, transcript: null };
      users.set(email, current);
      return clone({ user: current.user });
    },
    async login(body) {
      const email = credentials(body.email, body.password);
      const found = users.get(email);
      if (!found) fail(401, "invalid_credentials");
      current = found!;
      return clone({ user: current.user });
    },
    async logout() { current = null; },
    async me(): Promise<Session> { const a = account(); return clone({ user: a.user, profile: a.profile }); },
    async password(body) { account(); checkPassword(body.current_password, "current_password"); checkPassword(body.new_password, "new_password"); },
    async deleteAccount(body) { const a = account(); checkPassword(body.password); users.delete(a.user.email); current = null; },
    async profile(body) {
      const a = account();
      const curriculum = curricula.find((c) => c.curriculum_code === body.curriculum_code && c.university_code === "HUS");
      if (!curriculum) fail(404, "curriculum_not_found");
      if (curriculum!.status !== "active") fail(409, "curriculum_not_active");
      if (body.cohort_year !== undefined && (!Number.isInteger(body.cohort_year) || body.cohort_year < 2000 || body.cohort_year > 2100)) {
        fail(422, "validation_error", { cohort_year: "Khóa học từ 2000 đến 2100." });
      }
      const changed = a.profile?.curriculum_code !== body.curriculum_code;
      if (changed && a.transcript?.results.length) throw new ApiError(409, "transcript_not_empty", "Bảng điểm còn kết quả.", { results: a.transcript.results.length });
      if (changed) a.transcript = null;
      a.profile = { ...body, university_code: "HUS", semesters_completed: changed ? 0 : a.profile?.semesters_completed ?? 0, updated_at: now() };
      return clone(a.profile);
    },
    async transcript() {
      const a = selected();
      return clone(a.transcript ?? { curriculum_code: a.profile.curriculum_code, semesters_completed: 0, results: [] });
    },
    async saveTranscript(body) {
      const a = selected();
      if (!Number.isInteger(body.semesters_completed) || body.semesters_completed < 0 || body.semesters_completed > 12) {
        fail(422, "validation_error", { semesters_completed: "Số kỳ từ 0 đến 12." });
      }
      const fields: Record<string, string> = {};
      const seen = new Set<string>();
      body.results.forEach((r, i) => {
        if (seen.has(r.course_code)) fields[`results[${i}].course_code`] = "Mã học phần bị trùng.";
        seen.add(r.course_code);
        if (!Number.isInteger(r.semester) || r.semester < 1 || r.semester > body.semesters_completed) fields[`results[${i}].semester`] = "Kỳ học không hợp lệ.";
        if (!("exempted" in r && r.exempted) && (typeof r.score !== "number" || !Number.isFinite(r.score) || r.score < 0 || r.score > 10)) fields[`results[${i}].score`] = "Điểm từ 0 đến 10.";
      });
      if (Object.keys(fields).length) fail(422, "validation_error", fields);
      a.transcript = clone({ ...body, curriculum_code: a.profile.curriculum_code, results: [...body.results].sort((x, y) => x.course_code.localeCompare(y.course_code)), updated_at: now() });
      a.profile.semesters_completed = body.semesters_completed;
      return clone(a.transcript!);
    },
    async progress() {
      const a = selected();
      // Fixed contract response, not a second implementation of GPA or academic rules in the client.
      const sample = examples["6.9"][0];
      return clone({ ...baseProgress, university_code: "HUS", curriculum_code: a.profile.curriculum_code,
        semesters_completed: a.profile.semesters_completed, target_semester: a.profile.semesters_completed + 1,
        credits_earned: sample.credits_earned, graduation_conditions: sample.graduation_conditions }) as Progress;
    },
    onUnauthenticated: (notify) => { listeners.add(notify); return () => { listeners.delete(notify); }; },
  };
}
