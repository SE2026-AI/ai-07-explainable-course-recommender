import { useState } from "react";
import type { CatalogCourse, WhyNotResult } from "../api/types";

interface Props {
  courses: CatalogCourse[];
  disabled: boolean;
  onAsk(courseId: string): Promise<WhyNotResult | null>;
}

export function WhyNot({ courses, disabled, onAsk }: Props) {
  const [courseId, setCourseId] = useState("");
  const [result, setResult] = useState<WhyNotResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function ask() {
    if (!courseId) return;
    setBusy(true);
    try {
      setResult(await onAsk(courseId));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-labelledby="whynot-title">
      <h2 id="whynot-title">4. Vì sao (không) gợi ý môn này?</h2>
      <div className="row">
        <label>
          Môn học
          <select value={courseId} onChange={(e) => { setCourseId(e.target.value); setResult(null); }}>
            <option value="">— chọn môn —</option>
            {courses.map((c) => <option key={c.course_id} value={c.course_id}>{c.course_id} · {c.title}</option>)}
          </select>
        </label>
        <button type="button" onClick={ask} disabled={disabled || !courseId || busy}>{busy ? "Đang hỏi…" : "Giải thích"}</button>
      </div>
      {result && (
        <div className="card" aria-live="polite" data-testid="whynot-result">
          <p>
            <strong>{result.course_id}</strong>: {result.eligible ? `đủ điều kiện, hạng ${result.rank ?? "—"}` : "chưa thể học ngay"}
          </p>
          <ul className="reasons">
            {result.reasons.map((r, i) => <li key={i}><span className="code">{r.code}</span> {r.text}</li>)}
          </ul>
        </div>
      )}
    </section>
  );
}
