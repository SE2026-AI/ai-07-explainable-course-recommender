import type { ComponentName, EligibleCourse, IneligibleCourse, RecommendationResponse } from "../api/types";
import { COMPONENTS } from "../api/types";
import { ArrowIcon, CheckIcon, LockIcon } from "./Icons";

export const COMPONENT_LABEL: Record<ComponentName, string> = {
  goal_match: "Mục tiêu",
  interest_match: "Sở thích",
  preparation: "Chuẩn bị",
  workload_fit: "Khối lượng",
};

export const COMPONENT_COLOR: Record<ComponentName, string> = {
  goal_match: "var(--c-goal)",
  interest_match: "var(--c-interest)",
  preparation: "var(--c-prep)",
  workload_fit: "var(--c-workload)",
};

export function Swatch({ name }: { name: ComponentName }) {
  return <span className="swatch" style={{ background: COMPONENT_COLOR[name] }} aria-hidden="true" />;
}

/** Ranks from a what-if simulation, keyed by course id; shown as badges without reordering the baseline list. */
export type RankPreview = Record<string, { rank: number | null; score: number | null }>;

function Breakdown({ course }: { course: EligibleCourse }) {
  if (!course.components) return null;
  const parts = COMPONENTS.map((name) => ({ name, c: course.components![name] }));
  const label = parts
    .filter(({ c }) => c.available)
    .map(({ name, c }) => `${COMPONENT_LABEL[name]} +${(c.contribution * 100).toFixed(1)}`)
    .join(", ");
  return (
    <div>
      <div className="stack" role="img" aria-label={`Điểm ${course.course_id} gồm: ${label}`}>
        {parts.filter(({ c }) => c.available && c.contribution > 0).map(({ name, c }) => (
          <span key={name} style={{ width: `${c.contribution * 100}%`, background: COMPONENT_COLOR[name] }} />
        ))}
      </div>
      <dl className="parts" aria-label={`Thành phần điểm ${course.course_id}`}>
        {parts.map(({ name, c }) => (
          <div key={name} className={c.available ? "" : "missing"}>
            <dt><Swatch name={name} />{COMPONENT_LABEL[name]}</dt>
            {c.available ? (
              <dd>
                <div className="contrib">+{(c.contribution * 100).toFixed(1)}</div>
                <div className="formula">{Math.round((c.value ?? 0) * 100)}% × {Math.round(c.effective_weight * 100)}%</div>
              </dd>
            ) : (
              <dd>
                <div className="contrib">—</div>
                <div className="formula">không có dữ liệu</div>
              </dd>
            )}
          </div>
        ))}
      </dl>
    </div>
  );
}

function DeltaBadge({ before, after }: { before: number | null; after: number | null | undefined }) {
  if (before == null || after === undefined) return null;
  if (after == null) return <span className="delta down">rời danh sách</span>;
  const d = before - after;
  if (d > 0) return <span className="delta up">▲ lên {d} hạng</span>;
  if (d < 0) return <span className="delta down">▼ xuống {-d} hạng</span>;
  return <span className="delta">giữ hạng</span>;
}

function EligibleCard({ course, preview }: { course: EligibleCourse; preview?: RankPreview }) {
  const p = preview?.[course.course_id];
  const hours = course.workload_hours_per_week;
  return (
    <li className="card" data-testid={`eligible-${course.course_id}`}>
      <div className="card-head">
        <span className="rank" aria-label={course.rank ? `Hạng ${course.rank}` : "Chưa xếp hạng"}>{course.rank ?? "–"}</span>
        <div className="card-title">
          <div className="line">
            <span className="cid">{course.course_id}</span>
            <h4>{course.title}</h4>
            {preview && <DeltaBadge before={course.rank} after={p ? p.rank : undefined} />}
          </div>
          <p className="meta">{course.credits} tín chỉ{hours != null && ` · ~${hours} giờ/tuần`}</p>
        </div>
        <div className="score-box" title="Mức phù hợp theo quy tắc, không phải xác suất thành công">
          <div className="score">{course.score_percent != null ? `${course.score_percent}%` : "—"}</div>
          <div className="score-label">mức phù hợp</div>
          {p?.score != null && <div className="score-label">kịch bản {(p.score * 100).toFixed(1)}%</div>}
        </div>
      </div>
      <Breakdown course={course} />
      {course.reasons.length > 0 && (
        <ul className="reasons">
          {course.reasons.map((r, i) => (
            <li key={i} className={`reason reason-${r.code.toLowerCase()}`}>
              <CheckIcon />
              <span className="text">{r.text}</span>
              <span className="code">{r.code}</span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function BlockedCard({ course, readyIds }: { course: IneligibleCourse; readyIds: Set<string> }) {
  const path = [...course.transitive_missing_paths].sort((a, b) => b.length - a.length)[0]
    ?? [...course.direct_missing_prerequisite_ids, course.course_id];
  return (
    <li className="card blocked" data-testid={`ineligible-${course.course_id}`}>
      <div className="card-title">
        <div className="line">
          <span className="cid">{course.course_id}</span>
          <h3>{course.title}</h3>
        </div>
        <p className="meta">{course.credits} tín chỉ</p>
      </div>
      {path.length > 1 && (
        <ol className="path" aria-label={`Lộ trình: ${path.join(" rồi ")}`}>
          {path.map((id, i) => (
            <li key={id}>
              {i > 0 && <ArrowIcon />}
              <span className={`node${id === course.course_id ? " target" : readyIds.has(id) ? " ready" : ""}`}>{id}</span>
            </li>
          ))}
        </ol>
      )}
      <ul className="reasons">
        {course.reasons.map((r, i) => (
          <li key={i}>
            <LockIcon />
            <span className="text">{r.text}</span>
            <span className="code">{r.code}</span>
          </li>
        ))}
      </ul>
    </li>
  );
}

export function Results({ data, stale, preview }: { data: RecommendationResponse; stale: boolean; preview?: RankPreview }) {
  const readyIds = new Set(data.eligible.map((c) => c.course_id));
  return (
    <section className={`main-results results${stale ? " is-stale" : ""}`} aria-labelledby="results-title">
      <div className="results-head">
        <div>
          <div className="eyebrow">Bước 2 · kết quả</div>
          <h2 id="results-title">Môn nên học kỳ tới</h2>
        </div>
        <ul className="legend" aria-label="Chú thích thành phần điểm">
          {COMPONENTS.map((c) => <li key={c}><Swatch name={c} />{COMPONENT_LABEL[c]}</li>)}
        </ul>
      </div>
      <p className="provenance">
        <span>catalog {data.catalog_version}</span><span>thuật toán {data.algorithm_version}</span><span>request {data.request_id}</span>
      </p>
      {data.status === "empty" && <p className="empty">Không có môn nào đủ điều kiện học ngay. Xem lý do ở phần “Chưa đủ điều kiện”.</p>}
      {data.eligible.length > 0 && (
        <>
          <h3 className="group-title"><span className="dot" />Đủ điều kiện học ngay <span className="count">{data.eligible.length} môn</span></h3>
          <ol className="cards">{data.eligible.map((c) => <EligibleCard key={c.course_id} course={c} preview={preview} />)}</ol>
        </>
      )}
      {data.ineligible.length > 0 && (
        <>
          <h3 className="group-title blocked"><span className="dot" />Chưa đủ điều kiện <span className="count">{data.ineligible.length} môn · cần học trước</span></h3>
          <ul className="cards blocked">{data.ineligible.map((c) => <BlockedCard key={c.course_id} course={c} readyIds={readyIds} />)}</ul>
        </>
      )}
    </section>
  );
}
