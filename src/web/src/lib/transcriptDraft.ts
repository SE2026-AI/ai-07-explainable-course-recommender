// Bảng điểm đang nhập ở bước 4 (WEB-6, #39). Chỉ là dữ liệu ô nhập: client không tính đạt/trượt,
// GPA hay trạng thái; mọi con số đó lấy từ `POST .../transcript` (§6.10).
import type { CurriculumCourse } from "../api/schema";
import type { TranscriptBody, TranscriptResult } from "../api/transcript";

/** Một môn đã tick. `score` giữ nguyên chuỗi người dùng gõ để không làm mất "7," khi đang gõ. */
export interface DraftRow {
  semester: number;
  score: string;
  exempted: boolean;
}

/** Mã môn → dòng đã tick. Môn không có trong map là chưa tick. */
export type Draft = Record<string, DraftRow>;

/** Tick các môn có kỳ dự kiến ≤ N, kỳ học = kỳ dự kiến; giữ nguyên các môn đã tick sẵn. */
export function prefill(draft: Draft, courses: CurriculumCourse[], semesters: number): Draft {
  const next = { ...draft };
  for (const c of courses) {
    const planned = c.recommended_semester;
    if (planned && planned >= 1 && planned <= semesters && !next[c.course_code]) {
      next[c.course_code] = { semester: planned, score: "", exempted: false };
    }
  }
  return next;
}

/** Bỏ các dòng không còn hợp lệ khi số kỳ đã học giảm: kỳ học lớn hơn N thì kéo về N. */
export function clampDraft(draft: Draft, semesters: number): Draft {
  if (semesters < 1) return {};
  return Object.fromEntries(
    Object.entries(draft).map(([code, row]) => [code, { ...row, semester: Math.min(row.semester, semesters) }]),
  );
}

/** "7,5" và "7.5" đều là 7.5; rỗng hoặc không phải số thì `null`. */
export function parseScore(text: string): number | null {
  const t = text.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(t)) return null;
  return Number(t);
}

/** Môn đã tick nhưng chưa có điểm hợp lệ và không tick "Miễn": chưa gửi được. */
export function incompleteRows(draft: Draft): string[] {
  return Object.entries(draft)
    .filter(([, row]) => !row.exempted && parseScore(row.score) === null)
    .map(([code]) => code);
}

/**
 * Body của §6.10 theo thứ tự danh sách môn của khung. `codes[i]` là mã môn của `results[i]`,
 * để đổi đường dẫn lỗi `results[3].score` về đúng ô.
 */
export function toBody(
  draft: Draft,
  courses: CurriculumCourse[],
  semesters: number,
): { body: TranscriptBody; codes: string[] } {
  const results: TranscriptResult[] = [];
  const codes: string[] = [];
  const order = [...courses.map((c) => c.course_code), ...Object.keys(draft)];
  for (const code of new Set(order)) {
    const row = draft[code];
    if (!row) continue;
    const score = parseScore(row.score);
    if (row.exempted) results.push({ course_code: code, semester: row.semester, exempted: true });
    else if (score !== null) results.push({ course_code: code, semester: row.semester, score });
    else continue;
    codes.push(code);
  }
  return { body: { semesters_completed: semesters, results }, codes };
}

export type DraftField = "course_code" | "semester" | "score" | "exempted";

/** `results[3].score` → `{ course: codes[3], field: "score" }`; đường dẫn khác thì `null`. */
export function fieldTarget(path: string, codes: string[]): { course: string; field: DraftField } | null {
  const m = /^results\[(\d+)\](?:\.(course_code|semester|score|exempted))?$/.exec(path);
  if (!m) return null;
  const course = codes[Number(m[1])];
  if (!course) return null;
  return { course, field: (m[2] as DraftField | undefined) ?? "course_code" };
}

/** Body §6.10 (ví dụ file trong test/fixtures/transcripts/) → bản nháp. Dòng sai kiểu thì bỏ. */
export function fromBody(body: unknown): { semesters: number; draft: Draft } | null {
  if (!body || typeof body !== "object") return null;
  const { semesters_completed, results } = body as Record<string, unknown>;
  if (typeof semesters_completed !== "number" || !Array.isArray(results)) return null;
  const draft: Draft = {};
  for (const r of results as Record<string, unknown>[]) {
    if (!r || typeof r.course_code !== "string" || typeof r.semester !== "number") continue;
    draft[r.course_code] = {
      semester: r.semester,
      score: typeof r.score === "number" ? String(r.score) : "",
      exempted: r.exempted === true,
    };
  }
  return { semesters: semesters_completed, draft };
}

const key = (uni: string, curriculum: string) => `ai07.transcript.${uni}.${curriculum}`;

/** Bản nháp lưu trên máy người dùng, theo trường + khung. localStorage có thể bị chặn nên bọc try/catch. */
export function loadDraft(uni: string, curriculum: string): Draft {
  try {
    const raw = localStorage.getItem(key(uni, curriculum));
    return raw ? (fromBody(JSON.parse(raw))?.draft ?? {}) : {};
  } catch {
    return {};
  }
}

export function saveDraft(uni: string, curriculum: string, semesters: number, draft: Draft): void {
  try {
    const rows = Object.entries(draft).map(([course_code, r]) => ({
      course_code,
      semester: r.semester,
      ...(r.exempted ? { exempted: true } : parseScore(r.score) !== null ? { score: parseScore(r.score) } : {}),
    }));
    localStorage.setItem(key(uni, curriculum), JSON.stringify({ semesters_completed: semesters, results: rows }));
  } catch {
    /* Không lưu được thì vẫn dùng được trong phiên này. */
  }
}
