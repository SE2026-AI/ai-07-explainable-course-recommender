import { Link, useLocation } from "react-router-dom";
import type { CurriculumBlock } from "../../api/schema";
import { ErrorBanner } from "../../components/ErrorBanner";
import { IconArrowRight, IconSparkle } from "../../components/Icons";
import { ProgressBar } from "../../components/ProgressBar";
import { vn } from "../../lib/format";
import { useApi } from "../../lib/useApi";
import { useStudent } from "./StudentLayout";

/** "Xem tiến độ học tập" (§6.4). Tên khối lấy từ khung (§6.2), tên môn từ danh sách học phần (§6.3). */
export function ProfilePage() {
  const { client, ref, profile: p } = useStudent();
  const [curriculum, retryCurriculum] = useApi(
    (s) => client.curriculum(ref.uni, p.curriculum_code, s),
    [client, ref.uni, p.curriculum_code],
  );
  const [courses] = useApi(
    (s) => client.curriculumCourses(ref.uni, p.curriculum_code, s),
    [client, ref.uni, p.curriculum_code],
  );

  const blockByCode = new Map<string, CurriculumBlock>(
    curriculum.state === "ok" ? (curriculum.data.blocks ?? []).map((b) => [b.block_code, b]) : [],
  );
  const courseName = new Map(
    courses.state === "ok" ? courses.data.courses.map((c) => [c.course_code, c.course_name]) : [],
  );
  const blocks = p.blocks ?? [];
  const outstanding = p.outstanding_courses ?? [];
  const { search } = useLocation();
  const pct = p.total_credits > 0 ? Math.min(100, Math.round((p.credits_earned / p.total_credits) * 100)) : 0;

  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <h2>Tiến độ học tập</h2>
          <p>
            Học kỳ <span className="mono">{p.term}</span>
          </p>
        </div>
        <div className="progress-overview">
          <div
            className="ring"
            style={{ ["--pct" as string]: pct }}
            role="img"
            aria-label={`Đã tích lũy ${pct}% tín chỉ tốt nghiệp`}
          >
            <span className="ring-value">{pct}%</span>
            <span className="ring-label">tín chỉ</span>
          </div>
          <dl className="stat-grid">
            <div className="stat">
              <dt>Tín chỉ tích lũy</dt>
              <dd>
                {p.credits_earned} / {p.total_credits}
              </dd>
              <ProgressBar value={p.credits_earned} max={p.total_credits} label="Tín chỉ tích lũy" />
            </div>
            <div className="stat">
              <dt>Điểm trung bình (thang 4)</dt>
              {/* §3.2: gpa là null khi chưa có điểm nào; không hiện 0. */}
              <dd>{p.gpa === null || p.gpa === undefined ? <span className="muted">Chưa có điểm</span> : vn(p.gpa)}</dd>
            </div>
            <div className={`stat ${p.credits_outstanding > 0 ? "stat-warn" : ""}`}>
              <dt>Tín chỉ đang nợ</dt>
              <dd>{p.credits_outstanding}</dd>
            </div>
            <div className="stat">
              <dt>Vị trí trong lộ trình</dt>
              <dd>
                Kỳ {p.target_semester} · năm {p.year_of_study}
              </dd>
            </div>
            <div className="stat">
              <dt>Trần tín chỉ một học kỳ</dt>
              <dd>{p.max_credits_per_term}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="next-step">
        <span className="step-icon">
          <IconSparkle />
        </span>
        <div>
          <strong>Bước tiếp theo: xem gợi ý cho học kỳ {p.term}</strong>
          <p className="hint">Mỗi môn được gợi ý kèm lý do; bạn có thể chỉnh trọng số và thử các giả định.</p>
        </div>
        <Link className="button primary-link" to={`../recommendations${search}`} relative="path">
          Xem gợi ý <IconArrowRight />
        </Link>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Môn đang nợ</h2>
        </div>
        {outstanding.length === 0 ? (
          <p className="muted">Không có môn nào đang nợ.</p>
        ) : (
          <ul className="chips chips-warn">
            {outstanding.map((code) => (
              <li key={code}>
                <span className="mono">{code}</span> {courseName.get(code)}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Tiến độ từng khối kiến thức</h2>
        </div>
        {curriculum.state === "error" && <ErrorBanner error={curriculum.error} onRetry={retryCurriculum} />}
        {blocks.length === 0 ? (
          <p className="muted">Chưa có tín chỉ nào được tính vào khối kiến thức.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Khối</th>
                <th scope="col">Tên</th>
                <th scope="col">Đã đạt / yêu cầu</th>
                <th scope="col" className="w-40">
                  Tiến độ
                </th>
              </tr>
            </thead>
            <tbody>
              {blocks.map((b) => (
                <tr key={b.block_code}>
                  <td className="mono">{b.block_code}</td>
                  <td>
                    {blockByCode.get(b.block_code)?.block_name ?? ""}
                    {/* §6.2: client PHẢI tôn trọng counts_toward_total khi hiển thị tiến độ. */}
                    {!b.counts_toward_total && <span className="hint"> (không tính vào tổng tín chỉ)</span>}
                  </td>
                  <td>
                    {b.earned_credits} / {b.required_credits}
                  </td>
                  <td>
                    <ProgressBar value={b.earned_credits} max={b.required_credits} label={`Khối ${b.block_code}`} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {(p.interests ?? []).length > 0 && (
        <section className="panel">
          <div className="panel-head">
            <h2>Chủ đề quan tâm (tự khai)</h2>
          </div>
          <ul className="chips">
            {(p.interests ?? []).map((t) => (
              <li key={t} className="mono">
                {t}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
