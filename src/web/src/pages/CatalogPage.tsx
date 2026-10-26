import { useSearchParams } from "react-router-dom";
import type { ApiClient } from "../api/client";
import type { CurriculumBlock, CurriculumCourse } from "../api/schema";
import { ErrorBanner } from "../components/ErrorBanner";
import { Prerequisites } from "../components/Prerequisites";
import { useApi } from "../lib/useApi";

/** Khung CTĐT và danh sách học phần của một trường (§6.2, §6.3). */
export function CatalogPage({ client }: { client: ApiClient }) {
  const [params, setParams] = useSearchParams();
  const uni = params.get("uni") ?? "";
  const code = params.get("curriculum") ?? "";

  const [universities, retryUniversities] = useApi((s) => client.universities(s), [client]);
  const [curricula, retryCurricula] = useApi(uni ? (s) => client.curricula(uni, s) : null, [client, uni]);
  const [detail, retryDetail] = useApi(
    uni && code ? (s) => client.curriculum(uni, code, s) : null,
    [client, uni, code],
  );
  const [courses, retryCourses] = useApi(
    uni && code ? (s) => client.curriculumCourses(uni, code, s) : null,
    [client, uni, code],
  );

  function select(nextUni: string, nextCode = "") {
    const p = new URLSearchParams();
    if (nextUni) p.set("uni", nextUni);
    if (nextCode) p.set("curriculum", nextCode);
    setParams(p);
  }

  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <h2>Khung chương trình đào tạo</h2>
          <p>Chọn trường và khung để xem học phần cùng điều kiện tiên quyết.</p>
        </div>
        {universities.state === "error" && (
          <ErrorBanner error={universities.error} onRetry={retryUniversities} />
        )}
        {curricula.state === "error" && <ErrorBanner error={curricula.error} onRetry={retryCurricula} />}
        <div className="grid-2">
          <label>
            Trường
            <select
              value={uni}
              disabled={universities.state !== "ok"}
              onChange={(e) => select(e.target.value)}
            >
              <option value="">
                {universities.state === "loading" ? "Đang tải…" : "Chọn trường"}
              </option>
              {universities.state === "ok" &&
                universities.data.map((u) => (
                  <option key={u.university_code} value={u.university_code}>
                    {u.name} ({u.university_code})
                  </option>
                ))}
            </select>
          </label>
          <label>
            Khung chương trình
            <select
              value={code}
              disabled={curricula.state !== "ok"}
              onChange={(e) => select(uni, e.target.value)}
            >
              <option value="">{curricula.state === "loading" ? "Đang tải…" : "Chọn khung"}</option>
              {curricula.state === "ok" &&
                curricula.data.map((c) => (
                  <option key={c.curriculum_code} value={c.curriculum_code}>
                    {c.major_name} · {c.name} ({c.curriculum_code})
                  </option>
                ))}
            </select>
          </label>
        </div>
        {universities.state === "ok" && universities.data.length === 0 && (
          <p className="muted">Hệ thống chưa có trường nào.</p>
        )}
        {curricula.state === "ok" && curricula.data.length === 0 && (
          <p className="muted">Trường này chưa có khung chương trình nào.</p>
        )}
      </section>

      {detail.state === "loading" && <p role="status">Đang tải khung chương trình…</p>}
      {detail.state === "error" && <ErrorBanner error={detail.error} onRetry={retryDetail} />}
      {detail.state === "ok" && (
        <section className="panel">
          <div className="panel-head">
            <h2>
              {detail.data.major_name} · {detail.data.name}
            </h2>
            <p className="mono">{detail.data.curriculum_code}</p>
          </div>
          <dl className="facts">
            <div>
              <dt>Tổng tín chỉ</dt>
              <dd>{detail.data.total_credits}</dd>
            </div>
            <div>
              <dt>Số kỳ chuẩn</dt>
              <dd>{detail.data.standard_semesters}</dd>
            </div>
            <div>
              <dt>Trần tín chỉ / kỳ</dt>
              <dd>{detail.data.max_credits_per_term}</dd>
            </div>
            <div>
              <dt>Thang điểm</dt>
              <dd>
                đạt từ {detail.data.pass_score} / {detail.data.max_score}
              </dd>
            </div>
          </dl>
          <BlockTree blocks={detail.data.blocks ?? []} />
        </section>
      )}

      {courses.state === "loading" && <p role="status">Đang tải học phần…</p>}
      {/* Cùng một mã khung sai thì hai endpoint báo cùng lỗi; chỉ hiện một lần. */}
      {courses.state === "error" && detail.state !== "error" && (
        <ErrorBanner error={courses.error} onRetry={retryCourses} />
      )}
      {courses.state === "ok" && <CourseTable courses={courses.data.courses} />}
    </>
  );
}

function BlockTree({ blocks }: { blocks: CurriculumBlock[] }) {
  if (blocks.length === 0) return <p className="muted">Khung chưa có khối kiến thức.</p>;
  return (
    <table className="table">
      <caption>Khối kiến thức</caption>
      <thead>
        <tr>
          <th scope="col">Khối</th>
          <th scope="col">Tên</th>
          <th scope="col">Tín chỉ yêu cầu</th>
          <th scope="col">Ghi chú</th>
        </tr>
      </thead>
      <tbody>
        {blocks.map((b) => (
          <tr key={b.block_code}>
            <td className="mono">{b.block_code}</td>
            <td style={{ paddingLeft: b.parent_block_code ? "1.5rem" : undefined }}>{b.block_name}</td>
            <td>
              {b.required_credits}
              {!b.counts_toward_total && <span className="hint"> (không tính vào tổng)</span>}
            </td>
            <td className="hint">{b.note}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CourseTable({ courses }: { courses: CurriculumCourse[] }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Học phần</h2>
        <p>{courses.length} học phần, theo thứ tự của khung.</p>
      </div>
      {courses.length === 0 ? (
        <p className="muted">Khung này chưa có học phần nào.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Mã</th>
              <th scope="col">Tên học phần</th>
              <th scope="col">Tín chỉ</th>
              <th scope="col">Khối</th>
              <th scope="col">Kỳ dự kiến</th>
              <th scope="col">Tiên quyết</th>
            </tr>
          </thead>
          <tbody>
            {courses.map((c) => (
              <tr key={c.course_code}>
                <td className="mono">{c.course_code}</td>
                <td>
                  {c.course_name}
                  {c.is_required && <span className="hint"> · bắt buộc</span>}
                </td>
                <td>{c.credits}</td>
                <td className="mono">{c.block_code}</td>
                <td>{c.recommended_semester ?? "—"}</td>
                <td>
                  <Prerequisites groups={c.prerequisite_groups} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
