import type { SimulationResponse, Weights } from "../api/types";
import { COMPONENTS } from "../api/types";
import { COMPONENT_LABEL } from "./Results";

interface Props {
  weights: Weights;
  baseline: Weights | null;
  onChange(weights: Weights): void;
  onAdopt(): void;
  onReset(): void;
  simulation: SimulationResponse | null;
  loading: boolean;
  error: string | null;
}

const pct = (x: number | null | undefined) => (x == null ? "—" : `${(x * 100).toFixed(1)}%`);

export function WhatIf({ weights, baseline, onChange, onAdopt, onReset, simulation, loading, error }: Props) {
  const total = COMPONENTS.reduce((s, c) => s + weights[c], 0);
  const changed = baseline != null && COMPONENTS.some((c) => weights[c] !== baseline[c]);
  return (
    <section className="panel" aria-labelledby="whatif-title">
      <h2 id="whatif-title">2. Ưu tiên &amp; what-if</h2>
      <p className="hint">Kéo thanh trượt để xem thứ hạng thay đổi thế nào. Kết quả gốc giữ nguyên cho tới khi bạn bấm “Dùng làm gốc”.</p>
      {COMPONENTS.map((c) => (
        <label key={c} className="slider">
          <span>{COMPONENT_LABEL[c]}</span>
          <input type="range" min={0} max={1} step={0.05} value={weights[c]} aria-valuetext={`${Math.round(weights[c] * 100)}`}
            onChange={(e) => onChange({ ...weights, [c]: Number(e.target.value) })} />
          <output>{total > 0 ? Math.round((weights[c] / total) * 100) : 0}%</output>
        </label>
      ))}
      {total === 0 && <p className="field-error" role="alert">Cần ít nhất một ưu tiên lớn hơn 0.</p>}
      <div className="actions">
        <button type="button" onClick={onAdopt} disabled={!changed || total === 0}>Dùng làm gốc</button>
        <button type="button" className="secondary" onClick={onReset} disabled={!changed}>Hoàn tác</button>
      </div>

      {changed && (
        <div className="compare" aria-live="polite" aria-busy={loading}>
          <h3 className="sub">So sánh gốc → kịch bản {loading && <span className="muted">(đang tính…)</span>}</h3>
          {error && <p className="field-error" role="alert">{error}</p>}
          {simulation && !error && (
            <>
              <table>
                <thead>
                  <tr><th scope="col">Môn</th><th scope="col">Hạng</th><th scope="col">Điểm gốc</th><th scope="col">Điểm mới</th></tr>
                </thead>
                <tbody>
                  {simulation.changes.map((ch) => (
                    <tr key={ch.course_id} data-testid={`change-${ch.course_id}`}>
                      <th scope="row">{ch.course_id}</th>
                      <td>{ch.rank_before} → {ch.rank_after}{ch.rank_before !== ch.rank_after && <span className={ch.rank_after! < ch.rank_before! ? "up" : "down"}>{ch.rank_after! < ch.rank_before! ? " ▲" : " ▼"}</span>}</td>
                      <td>{pct(ch.score_before)}</td>
                      <td>{pct(ch.score_after)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(simulation.entered.length > 0 || simulation.exited.length > 0) && (
                <p className="muted">Vào danh sách: {simulation.entered.join(", ") || "—"} · Ra khỏi danh sách: {simulation.exited.join(", ") || "—"}</p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
