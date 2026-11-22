import { Link, useNavigate, useSearchParams } from "react-router-dom";
import type { ApiClient } from "../api/client";
import { ErrorBanner } from "../components/ErrorBanner";
import { IconArrowRight } from "../components/Icons";
import { useApi } from "../lib/useApi";
import { MAX_SEMESTERS, choiceQuery, isComplete, readChoice, type WizardChoice } from "../lib/wizard";

const SEMESTER_OPTIONS = Array.from({ length: MAX_SEMESTERS + 1 }, (_, i) => i);

/**
 * WEB-5 (#39): trang chủ là wizard để sinh viên tự nhập bảng điểm.
 * Bước 1 chọn trường, bước 2 chọn khung, bước 3 số kỳ đã học; bước 4 ở /bang-diem.
 * Không lưu gì lên server: lựa chọn nằm trên URL.
 */
export function TranscriptWizardPage({ client }: { client: ApiClient }) {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const picked = readChoice(params);

  const [universities, retryUniversities] = useApi((s) => client.universities(s), [client]);
  // Chỉ có một trường thì chọn sẵn, đỡ một bước bấm.
  const onlyUni =
    universities.state === "ok" && universities.data.length === 1 ? universities.data[0].university_code : "";
  const choice: WizardChoice = picked.uni ? picked : { ...picked, uni: onlyUni };
  const { uni, curriculum, semesters } = choice;

  const [curricula, retryCurricula] = useApi(uni ? (s) => client.curricula(uni, s) : null, [client, uni]);
  const chosenCurriculum =
    curricula.state === "ok" ? curricula.data.find((c) => c.curriculum_code === curriculum) : undefined;

  function update(next: WizardChoice) {
    setParams(new URLSearchParams(choiceQuery(next)), { replace: true });
  }

  const step = !uni ? 1 : !chosenCurriculum ? 2 : semesters === null ? 3 : 4;
  const ready = isComplete(choice) && Boolean(chosenCurriculum);

  return (
    <div className="wizard">
      <section className="wizard-intro">
        <p className="eyebrow-pill">Cố vấn học tập · AI-07</p>
        <h2 className="landing-title">Kỳ tới nên học môn gì, và vì sao?</h2>
        <p className="landing-lead">
          Tự nhập bảng điểm của bạn theo khung chương trình, hệ thống sẽ gợi ý học phần cho kỳ tới và nói rõ lý do. Bảng
          điểm chỉ dùng để tính gợi ý, không được lưu lên máy chủ.
        </p>
        <ol className="wizard-steps" aria-label="Các bước">
          {["Chọn trường", "Chọn khung chương trình", "Số kỳ đã học", "Nhập bảng điểm"].map((label, i) => (
            <li
              key={label}
              className={i + 1 < step ? "done" : i + 1 === step ? "current" : undefined}
              aria-current={i + 1 === step ? "step" : undefined}
            >
              <span className="wizard-dot">{i + 1}</span>
              {label}
            </li>
          ))}
        </ol>
      </section>

      <section className="panel wizard-card">
        {/* Bước 1 */}
        <fieldset className="wizard-field">
          <legend>
            <span className="wizard-num">1</span> Trường
          </legend>
          {universities.state === "error" && <ErrorBanner error={universities.error} onRetry={retryUniversities} />}
          {universities.state === "ok" && universities.data.length === 0 && (
            <p className="muted">Hệ thống chưa có trường nào.</p>
          )}
          <select
            aria-label="Trường"
            value={uni}
            disabled={universities.state !== "ok" || universities.data.length === 0}
            onChange={(e) => update({ uni: e.target.value, curriculum: "", semesters: null })}
          >
            <option value="">{universities.state === "loading" ? "Đang tải…" : "Chọn trường"}</option>
            {universities.state === "ok" &&
              universities.data.map((u) => (
                <option key={u.university_code} value={u.university_code}>
                  {u.name} ({u.university_code})
                </option>
              ))}
          </select>
        </fieldset>

        {/* Bước 2 */}
        {uni && (
          <fieldset className="wizard-field">
            <legend>
              <span className="wizard-num">2</span> Khung chương trình
            </legend>
            {curricula.state === "loading" && <p className="muted">Đang tải khung chương trình…</p>}
            {curricula.state === "error" && <ErrorBanner error={curricula.error} onRetry={retryCurricula} />}
            {curricula.state === "ok" && curricula.data.length === 0 && (
              <p className="muted">Trường này chưa có khung chương trình nào.</p>
            )}
            {curricula.state === "ok" && curricula.data.length > 0 && (
              <div className="option-cards">
                {curricula.data.map((c) => (
                  <label key={c.curriculum_code} className="option-card">
                    <input
                      type="radio"
                      name="curriculum"
                      value={c.curriculum_code}
                      checked={c.curriculum_code === curriculum}
                      onChange={() => update({ uni, curriculum: c.curriculum_code, semesters })}
                    />
                    <span className="option-body">
                      <strong>{c.major_name}</strong>
                      <span className="muted">
                        {c.name} · khóa từ {c.effective_from_cohort}
                      </span>
                      <span className="option-meta">
                        <span>{c.total_credits} tín chỉ</span>
                        <span>{c.standard_semesters} kỳ chuẩn</span>
                        <span className="mono">{c.curriculum_code}</span>
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            )}
            {curriculum && curricula.state === "ok" && !chosenCurriculum && (
              <p className="banner warn">Không có khung {curriculum} ở trường này, hãy chọn lại.</p>
            )}
          </fieldset>
        )}

        {/* Bước 3 */}
        {chosenCurriculum && (
          <fieldset className="wizard-field">
            <legend>
              <span className="wizard-num">3</span> Bạn đã học xong bao nhiêu kỳ?
            </legend>
            <p className="hint">
              Chọn 0 nếu bạn mới vào trường. Khung này có {chosenCurriculum.standard_semesters} kỳ chuẩn.
            </p>
            <div className="semester-grid" role="radiogroup" aria-label="Số kỳ đã học">
              {SEMESTER_OPTIONS.map((n) => (
                <label key={n} className="semester-chip">
                  <input
                    type="radio"
                    name="semesters"
                    value={n}
                    checked={semesters === n}
                    onChange={() => update({ uni, curriculum, semesters: n })}
                  />
                  <span>{n}</span>
                </label>
              ))}
            </div>
          </fieldset>
        )}

        <button
          type="button"
          className="primary wizard-next"
          disabled={!ready}
          onClick={() => navigate(`/bang-diem${choiceQuery(choice)}`)}
        >
          Tiếp tục: nhập bảng điểm <IconArrowRight />
        </button>
        <p className="hint wizard-alt">
          Chỉ muốn xem thử? <Link to="/students">Dùng sinh viên mẫu</Link>
        </p>
      </section>
    </div>
  );
}
