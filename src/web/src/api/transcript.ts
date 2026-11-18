// Kiểu của §6.10 `POST .../curricula/{code}/transcript`, khai báo tay theo api-contract.md.
// TẠM THỜI: openapi.json chưa có endpoint này (API-4, #38). Khi có, chạy `npm run gen:api`,
// thay các kiểu dưới đây bằng tên sinh tự động trong schema.ts rồi xóa file này.

/** Một dòng bảng điểm: có đúng một trong hai trường `score` và `exempted`. */
export type TranscriptResult =
  | { course_code: string; semester: number; score: number; exempted?: never }
  | { course_code: string; semester: number; exempted: true; score?: never };

export interface TranscriptBody {
  semesters_completed: number;
  results: TranscriptResult[];
}

export interface TranscriptBlock {
  block_code: string;
  required_credits: number;
  earned_credits: number;
  counts_toward_total: boolean;
}

export interface TranscriptCourse {
  course_code: string;
  course_name: string;
  credits: number;
  block_code: string;
  status: string;
  last_attempt?: { semester: number; score?: number | null; letter_grade?: string | null } | null;
  text: string;
}

export interface TranscriptWarning {
  code: string;
  course_code?: string | null;
  text: string;
  data?: Record<string, unknown>;
}

export interface Transcript {
  university_code: string;
  curriculum_code: string;
  semesters_completed: number;
  target_semester: number;
  credits_earned: number;
  credits_outstanding: number;
  total_credits: number;
  gpa: number | null;
  max_credits_per_term: number;
  outstanding_courses: string[];
  blocks: TranscriptBlock[];
  summary: { passed: number; retake: number; eligible: number; missing_prerequisite: number; block_complete: number };
  courses: TranscriptCourse[];
  warnings: TranscriptWarning[];
}
