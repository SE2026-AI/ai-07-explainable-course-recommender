import type { SimulationResponse, Weights } from "../api/types";
import { COMPONENTS } from "../api/types";
import { COMPONENT_LABEL, Swatch } from "./Results";

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
      <div>
        <div className="eyebrow">Bước 3</div>
        <h2 id="whatif-title">Ưu tiên &amp; what-if</h2>
        <p className="muted" style={{ marginTop: 6 }}>Kéo thanh trượt để xem thứ hạng thay đổi. Kết quả gốc giữ nguyên tới khi bạn bấm “Dùng làm gốc”.</p>
      </div>
      {COMPONENTS.map((c) => (
        <label key={c} className="slider">
          <span className="row">
            <span className="name"><Swatch name={c} />{COMPONENT_LABEL[c]}</span>
            <span className="out">{total > 0 ? Math.round((weights[c] / total) * 100) : 0}%</span>
          </span>
          <input type="range" min={0} max={1} step={0.05} value={weights[c]} aria-valuetext={`${Math.round(weights[c] * 100)}`}
            onChange={(e) => onChange({ ...weights, [c]: Number(e.target.value) })} />
        </label>
      ))}
      {total === 0 && <p className="field-error" role="alert">Cần ít nhất một ưu tiên lớn hơn 0.</p>}
      <div className="grid-2">
        <button type="button" className="primary" style={{ minHeight: 44, fontSize: "0.93rem" }} onClick={onAdopt} disabled={!changed || total === 0}>Dùng làm gốc</button>
        <button type="button" className="secondary" style={{ minHeight: 44 }} onClick={onReset} disabled={!changed}>Hoàn tác</button>
      </div>

      {changed && (
        <div className="compare" aria-live="polite" aria-busy={loading}>
          <h3>Gốc → kịch bản {loading && <span className="muted" style={{ textTransform: "none" }}>(đang tính…)</span>}</h3>
          {error && <p className="field-error" role="alert">{error}</p>}
          {simulation && !error && (
            <>
              <table>
                <thead>
                  <tr><th scope="col">Môn</th><th scope="col">Hạng</th><th scope="col">Gốc</th><th scope="col">Mới</th></tr>
                </thead>
                <tbody>
                  {simulation.changes.map((ch) => (
                    <tr key={ch.course_id} data-testid={`change-${ch.course_id}`}>
                      <th scope="row" className="mono">{ch.course_id}</th>
                      <td>
                        {ch.rank_before ?? "—"} → {ch.rank_after ?? "—"}
                        {ch.rank_before != null && ch.rank_after != null && ch.rank_before !== ch.rank_after && (
                          <span className={ch.rank_after < ch.rank_before ? "up" : "down"}>{ch.rank_after < ch.rank_before ? " ▲" : " ▼"}</span>
                        )}
                      </td>
                      <td>{pct(ch.score_before)}</td>
                      <td><strong>{pct(ch.score_after)}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(simulation.entered.length > 0 || simulation.exited.length > 0) && (
                <p className="muted" style={{ marginTop: 8 }}>Vào danh sách: {simulation.entered.join(", ") || "—"} · Ra khỏi danh sách: {simulation.exited.join(", ") || "—"}</p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
