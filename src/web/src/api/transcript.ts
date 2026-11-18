// Kiểu của §6.10 `POST .../curricula/{code}/transcript`, khai báo tay theo api-contract.md.
// TẠM THỜI: openapi.json chưa có endpoint này (API-4, #38). Khi có, chạy `npm run gen:api`,
// thay các kiểu dưới đây bằng tên sinh tự động trong schema.ts rồi xóa file này.
import type { RecommendationItem } from "./schema";

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

// §6.11 `POST .../curricula/{code}/recommendations`, cùng tình trạng tạm thời như trên (API-5, #38).

/** Body §6.10 cộng khoảng tín chỉ, trọng số và what-if. Vắng trường nào thì server dùng mặc định. */
export interface TranscriptRecommendationBody extends TranscriptBody {
  min_credits?: number;
  max_credits?: number;
  weights?: Record<string, number>;
  skip?: string[];
  include?: string[];
}

/** Môn học được mà không được xếp; `reason` theo §4.6: skipped, block_full, credit_budget. */
export interface NotSelected {
  course_code: string;
  course_name: string;
  credits: number;
  block_code: string;
  status: string;
  score: number;
  reason: string;
  text: string;
  data?: Record<string, unknown>;
}

export interface TranscriptRecommendations {
  university_code: string;
  curriculum_code: string;
  algorithm_version: string;
  what_if: boolean;
  weights: Record<string, number>;
  target_semester: number;
  credit_window: { min_credits: number; max_credits: number; total_credits: number; text: string };
  candidate_count: number;
  items: RecommendationItem[];
  not_selected: NotSelected[];
  not_eligible: {
    course_code: string;
    course_name: string;
    credits: number;
    block_code: string;
    status: string;
    missing_prerequisites?: string[][] | null;
    text?: string;
  }[];
  warnings: TranscriptWarning[];
}
