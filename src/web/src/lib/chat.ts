import type { TranscriptRecommendations } from "../api/transcript";

/**
 * Hỏi đáp về kết quả gợi ý §6.11, không dùng mô hình ngôn ngữ (README: mô hình ngôn ngữ không quyết định gợi
 * ý). Câu trả lời chỉ ghép câu chữ và con số server đã trả; mã môn duy nhất được nhắc ngoài dữ liệu là mã người
 * dùng tự gõ. Muốn thay bằng LLM ở backend thì giữ nguyên chữ ký `answerQuestion` và `Answer`.
 */
export interface Answer {
  text: string;
  lines?: string[];
  /** "Bỏ môn X thì sao?": màn gợi ý gọi lại API what-if với `skip`, không tự tính. */
  action?: { type: "skip"; course_code: string };
}

type Found =
  | { kind: "item"; code: string; name: string; rank: number; reasons: string[] }
  | { kind: "not_selected"; code: string; name: string; text: string }
  | { kind: "not_eligible"; code: string; name: string; text?: string };

/** Chữ thường, bỏ dấu, để "Giải tích 3" khớp "giai tich 3". */
function norm(s: string): string {
  return s.normalize("NFD").replace(/\p{M}/gu, "").replace(/đ/gi, "d").toLowerCase();
}

function courses(data: TranscriptRecommendations): Found[] {
  return [
    ...(data.items ?? []).map((c): Found => ({
      kind: "item",
      code: c.course_code,
      name: c.course_name,
      rank: c.rank,
      reasons: (c.reasons ?? []).flatMap((r) => (r.text ? [r.text] : [])),
    })),
    ...(data.not_selected ?? []).map((c): Found => ({
      kind: "not_selected",
      code: c.course_code,
      name: c.course_name,
      text: c.text,
    })),
    ...(data.not_eligible ?? []).map((c): Found => ({
      kind: "not_eligible",
      code: c.course_code,
      name: c.course_name,
      text: c.text,
    })),
  ];
}

const CODE = /\b[A-Z]{2,4}\d{3,4}[A-Z]?\b/gi;
const OUT_OF_SCOPE =
  /nghe nghiep|viec lam|xin viec|ra truong lam|muc luong|\bluong\b|doan diem|du doan|du doan diem|bao nhieu diem|co qua (mon|duoc)|co truot|hoc bong/;
// shortcut: khớp từ khóa, "bộ" cũng thành "bo"; thay bằng phân loại ý định ở backend khi có LLM.
const SKIP = /\b(bo|hoan|de sau)\b|khong hoc (mon|ky)/;
const CREDITS = /tin chi/;
const MISSING = /thieu|dieu kien|tien quyet|chua hoc duoc/;

/** Câu hỏi mẫu dựng từ chính kết quả: chỉ nhắc tên môn có trong dữ liệu. */
export function suggestions(data: TranscriptRecommendations): string[] {
  const first = data.items?.[0];
  const notYet = data.not_selected?.[0] ?? data.not_eligible?.[0];
  return [
    ...(first ? [`Vì sao gợi ý môn ${first.course_name}?`] : []),
    ...(notYet ? [`Vì sao chưa có môn ${notYet.course_name}?`] : []),
    "Kỳ này nên đăng ký bao nhiêu tín chỉ?",
    "Mình còn thiếu điều kiện gì?",
  ];
}

const HELP = "Bạn thử hỏi về một môn trong kết quả, ví dụ bấm một câu hỏi mẫu bên dưới.";

export function answerQuestion(question: string, data: TranscriptRecommendations): Answer {
  const q = norm(question.trim());
  if (!q) return { text: HELP };
  if (OUT_OF_SCOPE.test(q)) {
    return {
      text: "Câu này nằm ngoài phạm vi: hệ thống chỉ giải thích gợi ý học phần, không định hướng nghề nghiệp hay đoán điểm.",
      lines: [HELP],
    };
  }

  const all = courses(data);
  const typed = [...question.matchAll(CODE)].map((m) => m[0].toUpperCase());
  // Tên dài trước, để "Giải tích 3" không bị "Giải tích" khớp nhầm.
  const byName = [...all].sort((a, b) => b.name.length - a.name.length).find((c) => q.includes(norm(c.name)));
  const course = all.find((c) => typed.includes(c.code)) ?? byName;

  if (!course && typed.length > 0) {
    return { text: `Không thấy môn ${typed[0]} trong kết quả gợi ý lần này.`, lines: [HELP] };
  }

  if (course) {
    const label = `${course.name} (${course.code})`;
    if (SKIP.test(q) && !/vi sao|tai sao/.test(q)) {
      return course.kind === "item"
        ? {
            text: `Mình chuyển ${label} sang "Chưa học kỳ này" và tính lại gợi ý.`,
            action: { type: "skip", course_code: course.code },
          }
        : { text: `${label} không nằm trong danh sách gợi ý nên không cần bỏ.` };
    }
    if (course.kind === "item") {
      return {
        text: `${label} đứng hạng ${course.rank} trong gợi ý kỳ ${data.target_semester}.`,
        lines: course.reasons,
      };
    }
    if (course.kind === "not_selected") return { text: course.text };
    return { text: course.text ?? `${label} chưa học được ở kỳ này.` };
  }

  if (CREDITS.test(q)) {
    return {
      text: data.credit_window.text,
      lines: [`Danh sách gợi ý hiện có ${(data.items ?? []).length} môn.`],
    };
  }

  if (MISSING.test(q)) {
    const blocked = data.not_eligible ?? [];
    if (blocked.length === 0) return { text: "Không có môn nào bị chặn vì điều kiện tiên quyết." };
    const shown = blocked.slice(0, 5).map((c) => c.text ?? `${c.course_name} (${c.course_code}) chưa học được.`);
    return {
      text: `Có ${blocked.length} môn chưa học được hoặc đã xong:`,
      lines: blocked.length > 5 ? [...shown, `… và ${blocked.length - 5} môn khác ở mục bên dưới.`] : shown,
    };
  }

  return { text: "Mình chưa hiểu câu hỏi hoặc không thấy môn nào khớp trong kết quả.", lines: [HELP] };
}
