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
  "service_unavailable",
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
  unauthenticated: "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại để tiếp tục.",
  invalid_credentials: "Email hoặc mật khẩu chưa đúng. Hãy kiểm tra lại.",
  forbidden: "Bạn không có quyền thực hiện thao tác này, hoặc yêu cầu không hợp lệ.",
  plan_not_found: "Bạn chưa lưu kế hoạch cho học kỳ này.",
  user_not_found: "Không tìm thấy tài khoản này.",
  email_taken: "Email này đã được đăng ký. Hãy đăng nhập hoặc dùng email khác.",
  last_admin: "Không thể xóa tài khoản quản trị viên cuối cùng.",
  profile_required: "Hãy chọn khung chương trình trước khi nhập bảng điểm.",
  curriculum_not_active: "Khung này chưa được mở hoặc đã ngừng nhận sinh viên mới. Hãy chọn khung khác.",
  transcript_not_empty: "Bảng điểm còn kết quả của khung cũ. Hãy xuất file dự phòng và xóa bảng điểm trước khi đổi khung.",
  plan_read_only: "Kế hoạch của học kỳ đã qua chỉ có thể xem.",
  plan_version_conflict: "Kế hoạch đã được sửa ở nơi khác. Hãy tải lại trước khi tiếp tục.",
  undo_unavailable: "Không thể hoàn tác lần bỏ môn này. Hãy tải lại kế hoạch.",
  curriculum_exists: "Mã khung chương trình này đã tồn tại.",
  curriculum_not_draft: "Chỉ có thể sửa hoặc kích hoạt một khung đang ở trạng thái nháp.",
  curriculum_invalid: "Gói chương trình chưa hợp lệ. Hãy kiểm tra các dòng được báo lỗi.",
  too_many_attempts: "Bạn đã đăng nhập sai quá nhiều lần. Hãy chờ hết thời gian giới hạn rồi thử lại.",
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
  service_unavailable: "Máy chủ API đang chạy nhưng không kết nối được cơ sở dữ liệu. Hãy thử lại sau.",
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
