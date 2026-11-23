// §6.10 `POST .../curricula/{code}/transcript`: kiểu sinh tự động từ openapi.json (API-4, #38), lấy qua schema.ts.
// §6.11 bên dưới vẫn khai báo tay cho tới khi API-5 (#51) vào main; khi đó chạy `npm run gen:api` và thay nốt.
import type {
  RecommendationItem,
  TranscriptCourseStatusItem,
  TranscriptIn,
  TranscriptOut,
  TranscriptResultIn,
  TranscriptWarningOut,
} from "./schema";

/**
 * Một dòng bảng điểm. openapi.json cho cả `score` và `exempted` cùng tùy chọn; ở frontend thu hẹp lại
 * để mỗi dòng có đúng một trong hai trường, như api-contract.md §6.10.
 */
export type TranscriptResult = TranscriptResultIn &
  ({ score: number; exempted?: never } | { exempted: true; score?: never });

/** Body §6.10. Frontend luôn gửi `results` (có thể là mảng rỗng). */
export type TranscriptBody = Omit<TranscriptIn, "results"> & { results: TranscriptResult[] };

export type TranscriptCourse = TranscriptCourseStatusItem;
export type TranscriptWarning = TranscriptWarningOut;
export type Transcript = TranscriptOut;

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
  items?: RecommendationItem[];
  not_selected?: NotSelected[];
  not_eligible?: {
    course_code: string;
    course_name: string;
    credits: number;
    block_code: string;
    status: string;
    missing_prerequisites?: string[][] | null;
    text?: string;
  }[];
  warnings?: TranscriptWarning[];
}
