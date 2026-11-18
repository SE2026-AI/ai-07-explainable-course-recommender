// Lựa chọn của wizard bước 1–3 (WEB-5, #39) nằm trên query string, để tải lại trang, nút Back
// và bước 4 (/bang-diem) đọc lại được mà không cần state chung.

/** §6.10: `semesters_completed` trong [0, 12]. */
export const MAX_SEMESTERS = 12;

export interface WizardChoice {
  uni: string;
  curriculum: string;
  /** Số kỳ đã học; `null` là chưa chọn. */
  semesters: number | null;
}

export function readChoice(params: URLSearchParams): WizardChoice {
  const raw = params.get("ky");
  const n = raw !== null && /^\d{1,2}$/.test(raw) ? Number(raw) : NaN;
  return {
    uni: params.get("uni") ?? "",
    curriculum: params.get("curriculum") ?? "",
    semesters: Number.isInteger(n) && n >= 0 && n <= MAX_SEMESTERS ? n : null,
  };
}

/** Query string theo thứ tự trường → khung → số kỳ; bỏ các mục chưa chọn. */
export function choiceQuery({ uni, curriculum, semesters }: WizardChoice): string {
  const p = new URLSearchParams();
  if (uni) p.set("uni", uni);
  if (uni && curriculum) p.set("curriculum", curriculum);
  if (uni && curriculum && semesters !== null) p.set("ky", String(semesters));
  const text = p.toString();
  return text ? `?${text}` : "";
}

export const isComplete = (c: WizardChoice) => Boolean(c.uni && c.curriculum && c.semesters !== null);
