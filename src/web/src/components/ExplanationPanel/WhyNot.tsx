import { useState } from "react";
import type { WhyNotResult } from "../../lib/presentation";
import type { CatalogCourse } from "../../api/types";

interface Props {
  courses: CatalogCourse[];
  disabled: boolean;
  onAsk(courseId: string): Promise<WhyNotResult | null>;
}

export function WhyNot({ courses, disabled, onAsk }: Props) {
  const [courseId, setCourseId] = useState("");
  const [result, setResult] = useState<WhyNotResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(id: string) {
    setCourseId(id);
    setResult(null);
    setError("");
    setBusy(true);
    try {
      setResult(await onAsk(id));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Không tải được giải thích.",
      );
    } finally {
      setBusy(false);
    }
  }

  const title = courses.find((c) => c.course_id === result?.course_id)?.title;

  return (
    <section className="panel" aria-labelledby="whynot-title">
      <div>
        <div className="eyebrow">Hỏi nhanh</div>
        <h2 id="whynot-title">Vì sao (không) gợi ý?</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Chọn một môn để xem lý do.
        </p>
      </div>
      <div className="chip-grid" role="group" aria-label="Chọn môn học">
        {courses.map((c) => (
          <button
            key={c.course_id}
            type="button"
            className="chip mono"
            title={c.title}
            aria-pressed={courseId === c.course_id}
            disabled={disabled || busy}
            onClick={() => ask(c.course_id)}
          >
            {c.course_id}
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}
      {busy && (
        <p className="muted" role="status">
          Đang hỏi…
        </p>
      )}
      {result && (
        <div
          className={`why-result ${result.eligible ? "eligible" : "blocked"}`}
          aria-live="polite"
          data-testid="whynot-result"
        >
          <strong>
            {result.course_id}
            {title && ` · ${title}`}
          </strong>
          <p className="status">
            {result.eligible
              ? `Đủ điều kiện · hạng ${result.rank ?? "—"}${
                  result.score_percent != null
                    ? ` (${result.score_percent}%)`
                    : ""
                }`
              : result.reason_codes.includes("COMPLETED")
              ? "Đã hoàn thành"
              : "Chưa thể học ngay"}
          </p>
          {result.direct_missing_prerequisite_ids.length > 0 && (
            <p>
              Tiên quyết còn thiếu:{" "}
              {result.direct_missing_prerequisite_ids.join(", ")}
            </p>
          )}
          {result.transitive_missing_paths.map((path, i) => (
            <p key={i}>Lộ trình: {path.join(" → ")}</p>
          ))}
          {result.evidence_refs?.map((ref, i) => (
            <p className="provenance" key={i}>
              Nguồn: {ref.source} ? {ref.record_id}
            </p>
          ))}
          <ul>
            {result.reasons.map((r, i) => (
              <li key={i}>
                {r.text} <span className="code">{r.code}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
