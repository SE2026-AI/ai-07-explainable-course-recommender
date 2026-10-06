import { useMemo, useState } from "react";
import type { CatalogCourse, Profile, RecommendationResponse } from "../api/types";

interface Props {
  courses: CatalogCourse[];
  profile: Profile;
  data: RecommendationResponse | null;
  onNavigate(view: "recommend" | "roadmap"): void;
}

type Status = "passed" | "eligible" | "blocked" | "failed" | "unknown";
const STATUS_LABEL: Record<Status, string> = {
  passed: "Đã qua",
  eligible: "Học được ngay",
  blocked: "Chưa đủ điều kiện",
  failed: "Chưa đạt",
  unknown: "Chưa xét",
};

const W = 184, H = 76, COL_GAP = 72, ROW_GAP = 32, PAD = 24;

export function GraphView({ courses, profile, data, onNavigate }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const layout = useMemo(() => {
    const byId = new Map(courses.map((c) => [c.course_id, c]));
    const memo = new Map<string, number>();
    const depth = (id: string, seen = new Set<string>()): number => {
      if (memo.has(id)) return memo.get(id)!;
      if (seen.has(id)) return 0; // defensive: the catalog should be acyclic
      seen.add(id);
      const pre = (byId.get(id)?.mandatory_prerequisites ?? []).filter((p) => byId.has(p));
      const d = pre.length ? 1 + Math.max(...pre.map((p) => depth(p, seen))) : 0;
      memo.set(id, d);
      return d;
    };
    const cols: string[][] = [];
    [...courses].sort((a, b) => a.course_id.localeCompare(b.course_id)).forEach((c) => {
      (cols[depth(c.course_id)] ??= []).push(c.course_id);
    });
    const maxRows = Math.max(1, ...cols.map((c) => c?.length ?? 0));
    const height = PAD * 2 + maxRows * H + (maxRows - 1) * ROW_GAP;
    const pos = new Map<string, { x: number; y: number }>();
    cols.forEach((ids, ci) => {
      const colH = ids.length * H + (ids.length - 1) * ROW_GAP;
      const top = (height - colH) / 2;
      ids.forEach((id, ri) => pos.set(id, { x: PAD + ci * (W + COL_GAP), y: top + ri * (H + ROW_GAP) }));
    });
    const width = PAD * 2 + cols.length * W + (cols.length - 1) * COL_GAP;
    const edges = courses.flatMap((c) => c.mandatory_prerequisites.filter((p) => pos.has(p)).map((p) => ({ from: p, to: c.course_id })));
    return { pos, width, height, edges, byId };
  }, [courses]);

  const statusOf = useMemo(() => {
    const m = new Map<string, Status>();
    profile.history.forEach((h) => m.set(h.course_id, h.state === "passed" ? "passed" : h.state === "failed" ? "failed" : "unknown"));
    data?.eligible.forEach((c) => m.set(c.course_id, "eligible"));
    data?.ineligible.forEach((c) => m.set(c.course_id, "blocked"));
    return (id: string): Status => m.get(id) ?? "unknown";
  }, [profile.history, data]);

  const sel = selected ? layout.byId.get(selected) : null;
  const selEligible = data?.eligible.find((c) => c.course_id === selected);
  const selBlocked = data?.ineligible.find((c) => c.course_id === selected);
  const dependents = selected ? courses.filter((c) => c.mandatory_prerequisites.includes(selected)).map((c) => c.course_id) : [];

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Mũi tên đi từ môn tiên quyết sang môn cần nó · bấm vào một môn để xem chi tiết</div>
          <h1 className="page-title">Đồ thị môn tiên quyết</h1>
        </div>
        <ul className="legend graph-legend" aria-label="Chú thích">
          <li><span className="node-swatch passed" />Đã qua</li>
          <li><span className="node-swatch eligible" />Học được ngay</li>
          <li><span className="node-swatch blocked" />Chưa đủ điều kiện</li>
          <li><span className="node-swatch unknown" />Chưa xét</li>
        </ul>
      </div>
      {!data && (
        <div className="banner info">
          <span>Chưa có kết quả gợi ý nên chỉ tô màu môn đã học.{" "}
            <button type="button" className="link" onClick={() => onNavigate("recommend")}>Tạo gợi ý</button> để thấy môn nào học được ngay.</span>
        </div>
      )}

      <div className="split">
        <div className="panel graph-box split-main">
          <div className="graph-canvas" style={{ width: layout.width, height: layout.height }}>
            <svg width={layout.width} height={layout.height} aria-hidden="true" className="graph-edges">
              <defs>
                <marker id="g-head" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="#8A94A6" /></marker>
                <marker id="g-head-missing" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="#B4480B" /></marker>
              </defs>
              {layout.edges.map(({ from, to }) => {
                const a = layout.pos.get(from)!, b = layout.pos.get(to)!;
                const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x - 2, y2 = b.y + H / 2;
                const mx = (x1 + x2) / 2;
                const missing = statusOf(from) !== "passed";
                const active = selected === from || selected === to;
                return (
                  <path key={`${from}-${to}`} d={`M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`} fill="none"
                    stroke={missing ? "#B4480B" : "#8A94A6"} strokeWidth={active ? 3 : 2} strokeDasharray={missing ? "6 6" : undefined}
                    opacity={selected && !active ? 0.35 : 1} markerEnd={`url(#${missing ? "g-head-missing" : "g-head"})`} />
                );
              })}
            </svg>
            {courses.map((c) => {
              const p = layout.pos.get(c.course_id)!;
              const st = statusOf(c.course_id);
              return (
                <button key={c.course_id} type="button" className={`gnode ${st}${selected === c.course_id ? " is-selected" : ""}`}
                  style={{ left: p.x, top: p.y, width: W, height: H }} aria-pressed={selected === c.course_id}
                  onClick={() => setSelected(selected === c.course_id ? null : c.course_id)} data-testid={`node-${c.course_id}`}>
                  <span className="gnode-title"><b>{c.course_id}</b> · {c.title}</span>
                  <span className="gnode-sub">{STATUS_LABEL[st]}{st === "eligible" && data?.eligible.find((e) => e.course_id === c.course_id)?.score_percent != null
                    ? ` · ${data!.eligible.find((e) => e.course_id === c.course_id)!.score_percent}%` : ""}</span>
                </button>
              );
            })}
          </div>
        </div>

        <aside className="panel split-side" aria-live="polite">
          {!sel ? (
            <p className="muted">Chọn một môn trên đồ thị để xem môn tiên quyết, môn mở khóa và lý do.</p>
          ) : (
            <>
              <div>
                <div className="eyebrow mono">{sel.course_id}</div>
                <h2>{sel.title}</h2>
                <p className={`status inline ${statusOf(sel.course_id)}`}>{STATUS_LABEL[statusOf(sel.course_id)]}</p>
              </div>
              <dl className="facts">
                <div><dt>Tín chỉ</dt><dd>{sel.credits}</dd></div>
                <div><dt>Giờ/tuần</dt><dd>{sel.workload_hours_per_week ?? "—"}</dd></div>
                <div><dt>Tiên quyết</dt><dd className="mono">{sel.mandatory_prerequisites.join(", ") || "—"}</dd></div>
                <div><dt>Mở khóa</dt><dd className="mono">{dependents.join(", ") || "—"}</dd></div>
                {sel.recommended_preparation && sel.recommended_preparation.length > 0 && (
                  <div><dt>Nên chuẩn bị</dt><dd className="mono">{sel.recommended_preparation.join(", ")}</dd></div>
                )}
              </dl>
              {(selEligible ?? selBlocked) && (
                <ul className="reasons">
                  {(selEligible ?? selBlocked)!.reasons.map((r, i) => (
                    <li key={i}><span className="text">{r.text}</span><span className="code">{r.code}</span></li>
                  ))}
                </ul>
              )}
              {selBlocked && <button type="button" className="secondary" onClick={() => onNavigate("roadmap")}>Xếp lộ trình tới môn này</button>}
            </>
          )}
        </aside>
      </div>
    </main>
  );
}
