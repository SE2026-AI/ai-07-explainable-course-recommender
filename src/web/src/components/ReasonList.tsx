import type { RecommendationReason } from "../api/schema";
import { vn } from "../lib/format";

const REASON_LABEL: Record<string, string> = {
  outstanding_retake: "Môn đang nợ",
  overdue: "Trễ so với lộ trình",
  on_time: "Đúng kỳ dự kiến",
  unlocks: "Mở khóa môn khác",
  strong_topic: "Chủ đề bạn học tốt",
  interest: "Chủ đề bạn quan tâm",
};

export function reasonLabel(code: string): string {
  return REASON_LABEL[code] ?? code;
}

/**
 * Bảng giải thích một gợi ý. Vẽ đúng các lý do server trả về, theo thứ tự server đã sắp (§3.3):
 * lý do không áp dụng thì vắng mặt khỏi mảng (§4.4), nên không có ô cố định nào điền 0.
 */
export function ReasonList({ reasons, score }: { reasons: RecommendationReason[]; score: number }) {
  if (reasons.length === 0) return <p className="hint">Không có lý do nào góp điểm cho môn này.</p>;
  const top = Math.max(score, ...reasons.map((r) => r.contribution), 1e-9);
  return (
    <ul className="reasons">
      {reasons.map((r, i) => (
        <li key={`${r.code}-${i}`} className={`reason reason-${r.code}`}>
          <div className="reason-head">
            <span className="reason-label">{reasonLabel(r.code)}</span>
            <span className="mono">+{vn(r.contribution, 4)}</span>
          </div>
          <div className="reason-bar" aria-hidden="true">
            <span style={{ width: `${Math.max(2, (r.contribution / top) * 100)}%` }} />
          </div>
          {r.text && <p>{r.text}</p>}
          <ReasonData code={r.code} data={r.data ?? {}} />
        </li>
      ))}
    </ul>
  );
}

function codes(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

/** Phần chi tiết lấy từ `data` (§4.4). Mã lạ hoặc trường lạ thì bỏ qua (§9.5). */
function ReasonData({ code, data }: { code: string; data: Record<string, unknown> }) {
  const list = codes(data.course_codes);
  if (code === "unlocks" && list.length > 0)
    return (
      <p className="hint">
        Mở khóa:{" "}
        {list.map((c) => (
          <span key={c} className="mono chip-inline">
            {c}
          </span>
        ))}
      </p>
    );
  if (code === "strong_topic" && list.length > 0)
    return (
      <p className="hint">
        Tính từ các môn:{" "}
        {list.map((c) => (
          <span key={c} className="mono chip-inline">
            {c}
          </span>
        ))}
      </p>
    );
  return null;
}

/** §7: `score` phải bằng tổng `contribution`. Hiện ra để người dùng tự đối chiếu và bắt lỗi backend. */
export function ScoreCheck({ reasons, score }: { reasons: RecommendationReason[]; score: number }) {
  const sum = Math.round(reasons.reduce((t, r) => t + r.contribution, 0) * 1e4) / 1e4;
  const ok = Math.abs(sum - score) < 1e-9;
  return (
    <span className={ok ? "score-check ok" : "score-check bad"} title="Tổng đóng góp của các lý do">
      {ok ? `= tổng đóng góp ${vn(sum, 4)}` : `⚠ tổng đóng góp ${vn(sum, 4)} khác điểm ${vn(score, 4)}`}
    </span>
  );
}
