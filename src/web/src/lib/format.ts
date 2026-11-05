/** Số kiểu Việt Nam ("3,0"), cho các con số client hiện ra mà không có câu `text` của server đi kèm. */
export function vn(value: number, digits = 2): string {
  return value.toLocaleString("vi-VN", { minimumFractionDigits: 0, maximumFractionDigits: digits });
}
