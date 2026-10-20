// Lỗi theo §5 của docs/architecture/api-contract.md:
// {"error": {"code", "message", "details"}}; details là object, không có request_id.

/** Mã lỗi server trả về (bảng §5). */
export const SERVER_ERROR_CODES = [
  "university_not_found",
  "student_not_found",
  "curriculum_not_found",
  "course_not_found",
  "term_not_found",
  "route_not_found",
  "method_not_allowed",
  "no_primary_program",
  "validation_error",
  "internal_error",
  "http_error",
] as const;

/** Mã client tự đặt khi không nhận được phản hồi đúng §5. Không bao giờ đến từ server. */
export const CLIENT_ERROR_CODES = ["network_error", "bad_response"] as const;

/**
 * Lỗi phát sinh ở tầng định tuyến: client gọi sai đường dẫn hoặc phương thức.
 * Đây là lỗi lập trình, không phải lỗi dữ liệu của sinh viên.
 */
const ROUTING_ERROR_CODES = new Set<string>([
  "route_not_found",
  "method_not_allowed",
  "http_error",
]);

const USER_MESSAGES: Record<string, string> = {
  university_not_found: "Không tìm thấy trường này. Hãy chọn lại trường.",
  student_not_found:
    "Không tìm thấy sinh viên với mã này trong trường đã chọn. Hãy kiểm tra lại mã sinh viên.",
  curriculum_not_found: "Không tìm thấy chương trình đào tạo này trong trường đã chọn.",
  course_not_found: "Không tìm thấy học phần này.",
  term_not_found: "Học kỳ này không có trong lịch của trường.",
  route_not_found:
    "Lỗi lập trình: ứng dụng gọi một đường dẫn API không tồn tại. Hãy báo nhóm phát triển.",
  method_not_allowed:
    "Lỗi lập trình: ứng dụng gọi API bằng phương thức không được hỗ trợ. Hãy báo nhóm phát triển.",
  http_error: "Lỗi lập trình: yêu cầu gửi tới API không hợp lệ. Hãy báo nhóm phát triển.",
  no_primary_program: "Sinh viên chưa có chương trình đào tạo chính đang hoạt động.",
  validation_error: "Dữ liệu gửi đi chưa hợp lệ. Hãy kiểm tra lại các trường được đánh dấu.",
  internal_error: "Máy chủ gặp lỗi không lường trước. Hãy thử lại sau ít phút.",
  network_error: "Không kết nối được tới máy chủ API. Hãy kiểm tra mạng hoặc backend.",
  bad_response: "Máy chủ API trả về dữ liệu không đúng định dạng.",
};

export type ErrorDetails = Record<string, unknown>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ErrorDetails;

  constructor(status: number, code: string, message: string, details: ErrorDetails = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** Gọi sai đường dẫn hoặc phương thức: hiện như lỗi lập trình. */
  get isRoutingError(): boolean {
    return ROUTING_ERROR_CODES.has(this.code);
  }

  /** Câu tiếng Việt cho người dùng; mã chưa biết thì dùng `message` của server. */
  get userMessage(): string {
    return USER_MESSAGES[this.code] ?? this.message;
  }

  /** `details.fields` của `validation_error`: tên trường → lỗi. */
  get fieldErrors(): Record<string, string> {
    const fields = this.details.fields;
    if (!isObject(fields)) return {};
    return Object.fromEntries(
      Object.entries(fields).filter((e): e is [string, string] => typeof e[1] === "string"),
    );
  }

  /** Dựng ApiError từ body của một phản hồi lỗi; body sai §5 thành `bad_response`. */
  static fromBody(status: number, body: unknown): ApiError {
    const error = isObject(body) ? body.error : undefined;
    if (isObject(error) && typeof error.code === "string" && typeof error.message === "string") {
      const details = isObject(error.details) ? error.details : {};
      return new ApiError(status, error.code, error.message, details);
    }
    return new ApiError(status, "bad_response", `HTTP ${status}: phản hồi lỗi không đúng định dạng.`);
  }
}

export function userMessageFor(error: unknown): string {
  if (error instanceof ApiError) return error.userMessage;
  return error instanceof Error ? error.message : "Đã xảy ra lỗi không xác định.";
}

export function hasUserMessage(code: string): boolean {
  return code in USER_MESSAGES;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
