import { Link, useLocation } from "react-router-dom";
import type { PlanViolation } from "../../api/schema";
import { ErrorBanner } from "../../components/ErrorBanner";
import { ProgressBar } from "../../components/ProgressBar";
import { usePlan } from "../../lib/plan";
import { STATUS_ORDER, statusLabel } from "../../lib/status";
import { useApi } from "../../lib/useApi";
import { useStudent } from "./StudentLayout";

const VIOLATION_LABEL: Record<string, string> = {
  credit_limit_exceeded: "Vượt trần tín chỉ",
  missing_prerequisite: "Chưa đủ tiên quyết",
  already_passed: "Đã đạt rồi",
  block_limit_exceeded: "Vượt số tín chỉ của khối tự chọn",
  duplicate_course: "Trùng môn",
  not_in_curriculum: "Không thuộc chương trình",
};

/** "Kiểm tra kế hoạch học kỳ" (§6.7). Mỗi lần kế hoạch đổi thì hỏi lại server; client không tự xét. */
export function PlanPage() {
  const { client, ref, term } = useStudent();
  const plan = usePlan();
  const { search } = useLocation();
  const [status] = useApi((s) => client.courseStatus(ref, { term }, s), [client, ref.uni, ref.student, term]);
  const [check, retry] = useApi(
    (s) => client.planCheck(ref, { course_codes: plan.codes, ...(term ? { term } : {}) }, s),
    [client, ref.uni, ref.student, term, plan.codes.join("|")],
  );
  const courses = status.state === "ok" ? status.data.courses : [];
  const byCode = new Map(courses.map((c) => [c.course_code, c]));

  const violations = check.state === "ok" ? (check.data.violations ?? []) : [];
  // Một môn có thể có nhiều vi phạm (§6.7): gom theo môn, hiện hết.
  const byCourse = new Map<string, PlanViolation[]>();
  const general: PlanViolation[] = [];
  for (const v of violations) {
    if (v.course_code) byCourse.set(v.course_code, [...(byCourse.get(v.course_code) ?? []), v]);
    else general.push(v);
  }
  const listed = new Set(plan.codes);
  const orphan = [...byCourse.keys()].filter((c) => !listed.has(c));

  return (
    <div className="split">
      <section className="panel controls sticky">
        <h2>Kế hoạch học kỳ</h2>
        <label>
          Thêm học phần
          <select
            value=""
            onChange={(e) => e.target.value && plan.add(e.target.value)}
            disabled={status.state !== "ok"}
          >
            <option value="">{status.state === "loading" ? "Đang tải…" : "Chọn môn"}</option>
            {STATUS_ORDER.map((s) => (
              <optgroup key={s} label={statusLabel(s)}>
                {courses
                  .filter((c) => c.status === s && !plan.codes.includes(c.course_code))
                  .map((c) => (
                    <option key={c.course_code} value={c.course_code}>
                      {c.course_code} · {c.course_name} ({c.credits} TC)
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
        </label>
        <p className="hint">Có thể thêm từ trang Gợi ý hoặc Trạng thái học phần.</p>
        {plan.codes.length > 0 && (
          <button type="button" className="secondary" onClick={plan.clear}>
            Xóa cả kế hoạch
          </button>
        )}
        <aside className="note">
          <strong>Lưu ý:</strong> khi xét điều kiện tiên quyết, các môn khác <em>trong cùng kế hoạch</em> không được
          tính là đã đạt. Ví dụ muốn học Học máy (cần Xác suất - Thống kê) thì phải đạt Xác suất - Thống kê ở một học kỳ
          trước, không thể học cả hai trong cùng học kỳ.
        </aside>
      </section>

      <div className="results">
        {check.state === "loading" && <p role="status">Đang kiểm tra…</p>}
        {check.state === "error" && <ErrorBanner error={check.error} onRetry={retry} />}
        {check.state === "ok" && (
          <section className="panel">
            <div className="panel-head">
              <h2>
                {check.data.valid ? (
                  <span className="status status-passed">Hợp lệ</span>
                ) : (
                  <span className="status status-retake">Chưa hợp lệ</span>
                )}{" "}
                {violations.length > 0 && <span className="hint">{violations.length} vi phạm</span>}
              </h2>
              <p>
                {check.data.total_credits} / {check.data.max_credits_per_term} tín chỉ
              </p>
            </div>
            <div className={check.data.total_credits > check.data.max_credits_per_term ? "meter over" : "meter"}>
              <ProgressBar
                value={check.data.total_credits}
                max={check.data.max_credits_per_term}
                label="Tín chỉ của kế hoạch"
              />
            </div>
            <p className="hint">Tổng tín chỉ chỉ cộng các khối được tính vào tổng tín chỉ tốt nghiệp.</p>
            {general.length > 0 && <ViolationList violations={general} />}
            {plan.codes.length === 0 ? (
              <div className="empty">
                <p className="muted">Kế hoạch đang trống.</p>
                <p className="hint">Bắt đầu từ danh sách gợi ý: mỗi môn có nút “Thêm vào kế hoạch”.</p>
                <Link className="button secondary-link" to={`../recommendations${search}`} relative="path">
                  Mở trang Gợi ý
                </Link>
              </div>
            ) : (
              <ul className="course-list">
                {plan.codes.map((code) => {
                  const c = byCode.get(code);
                  const vs = byCourse.get(code) ?? [];
                  return (
                    <li key={code} className={`course-row ${vs.length ? "has-violation" : ""}`}>
                      <div className="course-main">
                        <div>
                          <span className="mono">{code}</span> <strong>{c?.course_name ?? ""}</strong>{" "}
                          {c && (
                            <span className="hint">
                              {c.credits} tín chỉ · khối {c.block_code}
                            </span>
                          )}
                        </div>
                        {vs.length > 0 ? (
                          <ViolationList violations={vs} />
                        ) : (
                          <p className="ok-text">Không có vi phạm.</p>
                        )}
                      </div>
                      <div className="course-side">
                        <button type="button" className="secondary small" onClick={() => plan.remove(code)}>
                          Bỏ
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
            {orphan.map((code) => (
              <div key={code}>
                <span className="mono">{code}</span>
                <ViolationList violations={byCourse.get(code) ?? []} />
              </div>
            ))}
          </section>
        )}
      </div>
    </div>
  );
}

function ViolationList({ violations }: { violations: PlanViolation[] }) {
  return (
    <ul className="violations">
      {violations.map((v, i) => (
        <li key={`${v.code}-${i}`}>
          <span className="violation-code">{VIOLATION_LABEL[v.code] ?? v.code}</span> {v.text}
        </li>
      ))}
    </ul>
  );
}
