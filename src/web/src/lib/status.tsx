// Nhãn hiển thị cho năm trạng thái của §4.1. Chỉ là nhãn: trạng thái do server quyết định.

export const STATUS_ORDER = ["retake", "eligible", "missing_prerequisite", "block_complete", "passed"] as const;

const LABEL: Record<string, string> = {
  retake: "Cần học lại",
  eligible: "Học được",
  missing_prerequisite: "Chưa đủ tiên quyết",
  block_complete: "Khối đã đủ tín chỉ",
  passed: "Đã đạt",
};

/** §4.1 cho phép thêm giá trị enum mới (`withdrawn`, `in_progress`); giá trị lạ hiện nguyên mã. */
export function statusLabel(status: string): string {
  return LABEL[status] ?? status;
}

export function statusClass(status: string): string {
  return `status status-${LABEL[status] ? status : "other"}`;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={statusClass(status)}>{statusLabel(status)}</span>;
}
