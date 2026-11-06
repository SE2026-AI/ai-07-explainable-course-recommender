import { useState } from "react";
import type { CourseStatusItem } from "../../api/schema";
import { ErrorBanner } from "../../components/ErrorBanner";
import { IconPlus, IconCheck, IconSearch } from "../../components/Icons";
import { Prerequisites } from "../../components/Prerequisites";
import { vn } from "../../lib/format";
import { usePlan } from "../../lib/plan";
import { STATUS_ORDER, StatusBadge, statusLabel } from "../../lib/status";
import { useApi } from "../../lib/useApi";
import { useStudent } from "./StudentLayout";

/** "Giải thích vì sao chưa" (§6.5): mọi học phần của khung, nhóm theo trạng thái. */
export function CourseStatusPage() {
  const { client, ref, term } = useStudent();
  const [status, retry] = useApi((s) => client.courseStatus(ref, { term }, s), [client, ref.uni, ref.student, term]);
  const [filter, setFilter] = useState("");
  const [only, setOnly] = useState<string | null>(null);

  if (status.state === "loading" || status.state === "idle") return <p role="status">Đang tải trạng thái học phần…</p>;
  if (status.state === "error") return <ErrorBanner error={status.error} onRetry={retry} />;

  const { summary, courses } = status.data;
  if (courses.length === 0) return <p className="panel muted">Khung chương trình chưa có học phần nào.</p>;

  const needle = filter.trim().toLowerCase();
  const shown = courses.filter(
    (c) =>
      (!only || c.status === only) && (!needle || `${c.course_code} ${c.course_name}`.toLowerCase().includes(needle)),
  );
  // §4.1 có thể thêm trạng thái mới: gom chúng vào cuối, không bỏ mất môn nào.
  const known = new Set<string>(STATUS_ORDER);
  const extra = [...new Set(courses.map((c) => c.status).filter((s) => !known.has(s)))];
  const summaryCount = summary as Record<string, number | undefined>;

  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <h2>Trạng thái học phần</h2>
          <p>
            Học kỳ <span className="mono">{status.data.term}</span> · {courses.length} học phần
          </p>
        </div>
        <ul className="summary" aria-label="Lọc theo trạng thái">
          {STATUS_ORDER.map((s) => (
            <li key={s}>
              <button
                type="button"
                className={`filter-chip filter-${s}`}
                aria-pressed={only === s}
                onClick={() => setOnly(only === s ? null : s)}
              >
                <span>{statusLabel(s)}</span> <strong>{summaryCount[s] ?? 0}</strong>
              </button>
            </li>
          ))}
        </ul>
        <label className="search">
          <span className="sr-only">Tìm học phần</span>
          <IconSearch />
          <input
            type="search"
            aria-label="Tìm học phần"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Tìm theo mã hoặc tên môn"
          />
        </label>
      </section>
      {[...STATUS_ORDER, ...extra].map((s) => {
        const group = shown.filter((c) => c.status === s);
        if (group.length === 0) return null;
        return (
          <details
            key={s}
            className={`panel group group-${s}`}
            open={only === s || !!needle || s === "retake" || s === "eligible"}
          >
            <summary>
              <h3>
                {statusLabel(s)} <span className="count">{group.length}</span>
              </h3>
            </summary>
            <ul className="course-list">
              {group.map((c) => (
                <CourseRow key={c.course_code} course={c} />
              ))}
            </ul>
          </details>
        );
      })}
      {shown.length === 0 && <p className="panel muted">Không có học phần nào khớp bộ lọc.</p>}
    </>
  );
}

function CourseRow({ course: c }: { course: CourseStatusItem }) {
  const plan = usePlan();
  const inPlan = plan.codes.includes(c.course_code);
  return (
    <li className="course-row">
      <div className="course-main">
        <div className="course-title">
          <strong>{c.course_name}</strong> <span className="mono muted">{c.course_code}</span>
          <span className="hint">
            {" "}
            · {c.credits} tín chỉ · khối {c.block_code}
          </span>
        </div>
        {/* Câu giải thích là của server (README: nhất quán trên mọi nền tảng); client không tự viết. */}
        {c.text && <p>{c.text}</p>}
        {c.missing_prerequisites && c.missing_prerequisites.length > 0 && (
          <p className="hint">
            Còn thiếu: <Prerequisites groups={c.missing_prerequisites} />
          </p>
        )}
        {c.last_attempt && (
          <p className="hint">
            Lần học gần nhất: học kỳ <span className="mono">{c.last_attempt.term_code}</span>, lần{" "}
            {c.last_attempt.attempt_no}
            {c.last_attempt.score === null || c.last_attempt.score === undefined
              ? " · được miễn"
              : ` · điểm ${vn(c.last_attempt.score, 1)}${c.last_attempt.letter_grade ? ` (${c.last_attempt.letter_grade})` : ""}`}
          </p>
        )}
        {c.block && (
          <p className="hint">
            Khối {c.block.block_name}: {c.block.earned_credits}/{c.block.required_credits} tín chỉ
          </p>
        )}
      </div>
      <div className="course-side">
        <StatusBadge status={c.status} />
        {/* Thêm được mọi môn: kế hoạch sai thì plan-check sẽ chỉ ra vi phạm, client không tự chặn. */}
        <button
          type="button"
          className={`small ${inPlan ? "in-plan" : "secondary"}`}
          aria-pressed={inPlan}
          onClick={() => (inPlan ? plan.remove(c.course_code) : plan.add(c.course_code))}
        >
          {inPlan ? <IconCheck /> : <IconPlus />}
          {inPlan ? "Trong kế hoạch" : "Thêm vào kế hoạch"}
        </button>
      </div>
    </li>
  );
}
