import { useMemo, useRef, useState, type PointerEvent, type WheelEvent } from "react";
import type { GraphEdge, GraphNode, PrerequisiteGraph } from "../api/schema";
import { statusClass, statusLabel } from "../lib/status";

const W = 170;
const H = 46;
const COL = 250;
const ROW = 62;
const PAD = 40;

export interface Layout {
  pos: Map<string, { x: number; y: number }>;
  width: number;
  height: number;
  /** Mỗi môn có tiên quyết: các nhóm theo group_no. Nhóm nối nhau bằng VÀ, mã trong nhóm bằng HOẶC (§4.2). */
  groups: Map<string, string[][]>;
}

/**
 * Xếp nút theo cột `recommended_semester` (môn không có kỳ dự kiến ở cột cuối), trong cột giữ thứ tự
 * server trả (§3.3). Gom cạnh theo môn rồi theo `group_no` để giữ VÀ/HOẶC (§6.9); không làm phẳng.
 */
export function layout(nodes: GraphNode[], edges: GraphEdge[]): Layout {
  const sems = [...new Set(nodes.map((n) => n.recommended_semester ?? Infinity))].sort((a, b) => a - b);
  const colOf = new Map(sems.map((s, i) => [s, i]));
  const rows = new Map<number, number>();
  const pos = new Map<string, { x: number; y: number }>();
  for (const n of nodes) {
    const col = colOf.get(n.recommended_semester ?? Infinity) ?? 0;
    const row = rows.get(col) ?? 0;
    rows.set(col, row + 1);
    pos.set(n.course_code, { x: PAD + col * COL, y: PAD + 28 + row * ROW });
  }
  const groups = new Map<string, Map<number, string[]>>();
  for (const e of edges) {
    const byNo = groups.get(e.course_code) ?? new Map<number, string[]>();
    byNo.set(e.group_no, [...(byNo.get(e.group_no) ?? []), e.required_course_code]);
    groups.set(e.course_code, byNo);
  }
  const maxRows = Math.max(1, ...rows.values());
  return {
    pos,
    width: PAD * 2 + (sems.length - 1) * COL + W,
    height: PAD * 2 + 28 + maxRows * ROW,
    groups: new Map(
      [...groups].map(([c, byNo]) => [c, [...byNo.entries()].sort((a, b) => a[0] - b[0]).map(([, g]) => g)]),
    ),
  };
}

function curve(x1: number, y1: number, x2: number, y2: number): string {
  const dx = Math.max(40, Math.abs(x2 - x1) / 2);
  return `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
}

export function PrereqGraph({
  graph,
  statusOf,
  keyCourses,
  block,
}: {
  graph: PrerequisiteGraph;
  statusOf: Map<string, string>;
  /** Môn then chốt: mã → số môn mở khóa, lấy từ `data.count` của lý do `unlocks`. */
  keyCourses: Map<string, number>;
  /** Lọc theo khối: chỉ làm nổi các môn thuộc khối này (tiền tố mã khối). */
  block: string;
}) {
  const nodes = useMemo(() => graph.nodes ?? [], [graph]);
  const edges = useMemo(() => graph.edges ?? [], [graph]);
  const L = useMemo(() => layout(nodes, edges), [nodes, edges]);
  const [focus, setFocus] = useState<string | null>(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);

  const related = useMemo(() => {
    if (!focus) return null;
    const set = new Set([focus]);
    for (const e of edges) {
      if (e.course_code === focus) set.add(e.required_course_code);
      if (e.required_course_code === focus) set.add(e.course_code);
    }
    return set;
  }, [focus, edges]);
  const inBlock = (code: string) => {
    const b = nodes.find((n) => n.course_code === code)?.block_code ?? "";
    return !block || b === block || b.startsWith(`${block}.`);
  };
  const dim = (code: string) => (related ? !related.has(code) : !inBlock(code));

  const sems = [...new Set(nodes.map((n) => n.recommended_semester ?? null))].sort(
    (a, b) => (a ?? Infinity) - (b ?? Infinity),
  );

  function onWheel(e: WheelEvent) {
    e.preventDefault();
    zoom(e.deltaY < 0 ? 1.15 : 1 / 1.15);
  }
  function zoom(f: number) {
    setView((v) => ({ ...v, k: Math.min(3, Math.max(0.3, v.k * f)) }));
  }
  function down(e: PointerEvent<SVGSVGElement>) {
    drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }
  function move(e: PointerEvent) {
    const d = drag.current;
    if (d) setView((v) => ({ ...v, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y }));
  }

  return (
    <div className="graph">
      <div className="graph-tools">
        <button type="button" className="icon" aria-label="Phóng to" onClick={() => zoom(1.25)}>
          +
        </button>
        <button type="button" className="icon" aria-label="Thu nhỏ" onClick={() => zoom(0.8)}>
          −
        </button>
        <button type="button" className="secondary small" onClick={() => setView({ x: 0, y: 0, k: 1 })}>
          Về vị trí đầu
        </button>
        {focus && (
          <button type="button" className="secondary small" onClick={() => setFocus(null)}>
            Bỏ chọn {focus}
          </button>
        )}
      </div>
      <svg
        role="img"
        aria-label="Sơ đồ tiên quyết"
        className="graph-canvas"
        viewBox={`0 0 ${Math.max(L.width, 600)} ${Math.max(L.height, 300)}`}
        onWheel={onWheel}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={() => (drag.current = null)}
        onPointerLeave={() => (drag.current = null)}
      >
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="arrow-head" />
          </marker>
        </defs>
        <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
          {sems.map((s, i) => (
            <text key={String(s)} x={PAD + i * COL} y={PAD} className="col-label">
              {s === null ? "Không có kỳ dự kiến" : `Kỳ ${s}`}
            </text>
          ))}
          {[...L.groups].flatMap(([target, groups]) => {
            const t = L.pos.get(target);
            if (!t) return [];
            const tx = t.x;
            const ty = t.y + H / 2;
            return groups.map((group, gi) => {
              const faded = dim(target) && group.every(dim);
              const key = `${target}-${gi}`;
              if (group.length === 1) {
                const s = L.pos.get(group[0]);
                if (!s) return null;
                return (
                  <path
                    key={key}
                    data-edge={`${group[0]}>${target}`}
                    className={`edge and ${faded ? "faded" : ""}`}
                    d={curve(s.x + W, s.y + H / 2, tx, ty)}
                    markerEnd="url(#arrow)"
                  />
                );
              }
              // Nhóm HOẶC: các cạnh nét đứt gặp nhau tại một nút "hoặc", rồi một cạnh liền vào môn đích.
              const jx = tx - 34;
              const jy = ty + (gi - (groups.length - 1) / 2) * 10;
              return (
                <g key={key} className={faded ? "faded" : ""} data-or-group={`${target}:${group.join("|")}`}>
                  {group.map((src) => {
                    const s = L.pos.get(src);
                    return s ? (
                      <path key={src} data-edge={`${src}>${target}`} className="edge or" d={curve(s.x + W, s.y + H / 2, jx - 6, jy)} />
                    ) : null;
                  })}
                  <circle cx={jx} cy={jy} r={6} className="or-node" />
                  <path className="edge and" d={`M${jx + 6},${jy} L${tx},${ty}`} markerEnd="url(#arrow)" />
                </g>
              );
            });
          })}
          {nodes.map((n) => {
            const p = L.pos.get(n.course_code)!;
            const st = statusOf.get(n.course_code);
            const unlocks = keyCourses.get(n.course_code);
            return (
              <g
                key={n.course_code}
                data-node={n.course_code}
                className={`node ${st ? statusClass(st) : ""} ${dim(n.course_code) ? "faded" : ""} ${unlocks ? "key" : ""} ${focus === n.course_code ? "focused" : ""}`}
                transform={`translate(${p.x},${p.y})`}
                onPointerDown={(e) => e.stopPropagation()}
                onClick={() => setFocus(focus === n.course_code ? null : n.course_code)}
              >
                <title>
                  {`${n.course_code} · ${n.course_name} · ${n.credits} tín chỉ · khối ${n.block_code}`}
                  {st ? ` · ${statusLabel(st)}` : ""}
                  {unlocks ? ` · mở khóa ${unlocks} môn` : ""}
                </title>
                <rect width={W} height={H} rx={8} />
                <text x={10} y={18} className="node-code">
                  {n.course_code}
                  {unlocks ? ` ★${unlocks}` : ""}
                </text>
                <text x={10} y={35} className="node-name">
                  {n.course_name.length > 24 ? `${n.course_name.slice(0, 23)}…` : n.course_name}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
