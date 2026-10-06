import type { ComponentName, EligibleCourse, IneligibleCourse, RecommendationResponse } from "../api/types";
import { COMPONENTS } from "../api/types";

export const COMPONENT_LABEL: Record<ComponentName, string> = {
  goal_match: "Mục tiêu",
  interest_match: "Sở thích",
  preparation: "Chuẩn bị",
  workload_fit: "Khối lượng",
};

function Breakdown({ course }: { course: EligibleCourse }) {
  if (!course.components) return null;
  return (
    <dl className="breakdown" aria-label={`Thành phần điểm ${course.course_id}`}>
      {COMPONENTS.map((name) => {
        const c = course.components![name];
        return (
          <div key={name} className={c.available ? "" : "missing"}>
            <dt>{COMPONENT_LABEL[name]}</dt>
            <dd>
              {c.available ? (
                <>
                  <span className="bar" aria-hidden="true"><span style={{ width: `${Math.round((c.value ?? 0) * 100)}%` }} /></span>
                  <span className="num">{Math.round((c.value ?? 0) * 100)}% × {Math.round(c.effective_weight * 100)}% = +{(c.contribution * 100).toFixed(1)}</span>
                </>
              ) : (
                <span className="num">không có dữ liệu</span>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

function EligibleCard({ course }: { course: EligibleCourse }) {
  return (
    <li className="card" data-testid={`eligible-${course.course_id}`}>
      <div className="card-head">
        <span className="rank" aria-label={course.rank ? `Hạng ${course.rank}` : "Chưa xếp hạng"}>{course.rank ?? "–"}</span>
        <div>
          <h3>{course.course_id} · {course.title}</h3>
          <p className="muted">{course.credits} tín chỉ{course.workload_hours_per_week != null && ` · ~${course.workload_hours_per_week} giờ/tuần`}</p>
        </div>
        <span className="score" title="Mức phù hợp theo quy tắc, không phải xác suất thành công">
          {course.score_percent != null ? `${course.score_percent}%` : "—"}
        </span>
      </div>
      <Breakdown course={course} />
      {course.reasons.length > 0 && (
        <ul className="reasons">
          {course.reasons.map((r, i) => (
            <li key={i} className={`reason reason-${r.code.toLowerCase()}`}>
              <span className="code">{r.code}</span> {r.text}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function BlockedCard({ course }: { course: IneligibleCourse }) {
  return (
    <li className="card blocked" data-testid={`ineligible-${course.course_id}`}>
      <h3>{course.course_id} · {course.title}</h3>
      <ul className="reasons">
        {course.reasons.map((r, i) => (
          <li key={i}><span className="code">{r.code}</span> {r.text}</li>
        ))}
      </ul>
    </li>
  );
}

export function Results({ data, stale }: { data: RecommendationResponse; stale: boolean }) {
  return (
    <section className={`panel results${stale ? " is-stale" : ""}`} aria-labelledby="results-title" aria-busy={false}>
      <h2 id="results-title">3. Gợi ý</h2>
      <p className="provenance">
        catalog <code>{data.catalog_version}</code> · thuật toán <code>{data.algorithm_version}</code> · request <code>{data.request_id}</code>
      </p>
      {data.status === "empty" && <p className="empty">Không có môn nào đủ điều kiện học ngay. Xem lý do ở phần “Chưa đủ điều kiện”.</p>}
      {data.eligible.length > 0 && (
        <>
          <h3 className="sub">Đủ điều kiện học ngay ({data.eligible.length})</h3>
          <ol className="cards">{data.eligible.map((c) => <EligibleCard key={c.course_id} course={c} />)}</ol>
        </>
      )}
      {data.ineligible.length > 0 && (
        <>
          <h3 className="sub">Chưa đủ điều kiện ({data.ineligible.length})</h3>
          <ul className="cards">{data.ineligible.map((c) => <BlockedCard key={c.course_id} course={c} />)}</ul>
        </>
      )}
    </section>
  );
}
