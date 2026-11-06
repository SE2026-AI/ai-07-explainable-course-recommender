import { useMemo, useState } from "react";
import { ErrorBanner } from "../../components/ErrorBanner";
import { PrereqGraph } from "../../components/PrereqGraph";
import { STATUS_ORDER, StatusBadge } from "../../lib/status";
import { useApi } from "../../lib/useApi";
import { useStudent } from "./StudentLayout";

/** Sơ đồ tiên quyết (§6.9), tô màu theo trạng thái của sinh viên đang xem (§6.5). */
export function GraphPage() {
  const { client, ref, term, profile } = useStudent();
  const code = profile.curriculum_code;
  const [graph, retry] = useApi((s) => client.prerequisiteGraph(ref.uni, code, s), [client, ref.uni, code]);
  const [status] = useApi((s) => client.courseStatus(ref, { term }, s), [client, ref.uni, ref.student, term]);
  // Môn then chốt lấy từ data.count của lý do unlocks (§4.4), trong tối đa 20 gợi ý của học kỳ này.
  const [recs] = useApi((s) => client.recommendations(ref, { term, limit: 20 }, s), [client, ref.uni, ref.student, term]);
  const [curriculum] = useApi((s) => client.curriculum(ref.uni, code, s), [client, ref.uni, code]);
  const [block, setBlock] = useState("");

  const statusOf = useMemo(
    () => new Map(status.state === "ok" ? status.data.courses.map((c) => [c.course_code, c.status]) : []),
    [status],
  );
  const keyCourses = useMemo(() => {
    const m = new Map<string, number>();
    if (recs.state !== "ok") return m;
    for (const it of recs.data.items ?? [])
      for (const r of it.reasons ?? []) {
        const count = r.code === "unlocks" ? Number(r.data?.count) : NaN;
        if (Number.isFinite(count) && count >= 3) m.set(it.course_code, count);
      }
    return m;
  }, [recs]);

  if (graph.state === "loading" || graph.state === "idle") return <p role="status">Đang tải sơ đồ…</p>;
  if (graph.state === "error") return <ErrorBanner error={graph.error} onRetry={retry} />;
  if ((graph.data.nodes ?? []).length === 0) return <p className="panel muted">Khung chương trình chưa có học phần nào.</p>;

  const blocks = curriculum.state === "ok" ? (curriculum.data.blocks ?? []) : [];
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Sơ đồ tiên quyết</h2>
        <p>
          {graph.data.nodes?.length} học phần · <span className="mono">{graph.data.curriculum_code}</span>
        </p>
      </div>
      <div className="graph-bar">
        <label>
          Làm nổi khối
          <select value={block} onChange={(e) => setBlock(e.target.value)}>
            <option value="">Tất cả</option>
            {blocks.map((b) => (
              <option key={b.block_code} value={b.block_code}>
                {b.block_code} · {b.block_name}
              </option>
            ))}
          </select>
        </label>
        <ul className="legend">
          {STATUS_ORDER.map((s) => (
            <li key={s}>
              <StatusBadge status={s} />
            </li>
          ))}
          <li>
            <span className="legend-line and" /> bắt buộc (VÀ)
          </li>
          <li>
            <span className="legend-line or" />
            <span className="or-dot" /> chỉ cần một trong các môn (HOẶC)
          </li>
          <li>★ môn then chốt: số môn mở khóa</li>
        </ul>
      </div>
      <p className="hint">
        Mũi tên đi từ môn phải đạt trước tới môn được mở khóa. Bấm một môn để chỉ xem các môn nối với nó; kéo để di
        chuyển, cuộn để phóng to.
      </p>
      <PrereqGraph graph={graph.data} statusOf={statusOf} keyCourses={keyCourses} block={block} />
    </section>
  );
}
