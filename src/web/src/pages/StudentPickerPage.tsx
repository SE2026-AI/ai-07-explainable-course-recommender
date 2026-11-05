import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { ApiClient } from "../api/client";
import { ErrorBanner } from "../components/ErrorBanner";
import { IconCalendar, IconList, IconSparkle } from "../components/Icons";
import { useApi } from "../lib/useApi";

/**
 * Chọn trường rồi nhập mã sinh viên. v1 không có xác thực (§2, §8) nên không có đăng nhập:
 * cặp mã trường + mã sinh viên là đủ để định danh (§1.3).
 */
/** Mã có trong data/seed, để người xem thử không phải đi tìm mã. */
const SAMPLE_CODES = ["26000001", "25000001", "24000001", "23000001"];

const STEPS = [
  [IconList, "Xem tiến độ", "Tín chỉ tích lũy, môn đang nợ và tiến độ từng khối kiến thức."],
  [
    IconSparkle,
    "Nhận gợi ý có giải thích",
    "Mỗi môn kèm lý do và mức đóng góp vào điểm, có thể chỉnh trọng số và thử giả định.",
  ],
  [IconCalendar, "Lập kế hoạch học kỳ", "Chọn môn, hệ thống kiểm tra tiên quyết và trần tín chỉ ngay."],
] as const;

export function StudentPickerPage({ client }: { client: ApiClient }) {
  const navigate = useNavigate();
  const [universities, retry] = useApi((s) => client.universities(s), [client]);
  const [uni, setUni] = useState("");
  const [code, setCode] = useState("");
  const chosenUni =
    uni || (universities.state === "ok" && universities.data.length === 1 ? universities.data[0].university_code : "");

  function submit(e: FormEvent) {
    e.preventDefault();
    const student = code.trim();
    if (!chosenUni || !student) return;
    navigate(`/students/${encodeURIComponent(chosenUni)}/${encodeURIComponent(student)}/profile`);
  }

  return (
    <div className="landing">
      <section className="landing-intro">
        <p className="eyebrow-pill">Cố vấn học tập · AI-07</p>
        <h2 className="landing-title">Kỳ tới nên học môn gì, và vì sao?</h2>
        <p className="landing-lead">
          Hệ thống đọc kết quả học tập và khung chương trình đào tạo để gợi ý học phần cho học kỳ tới. Mọi gợi ý đều nói
          rõ lý do, không có hộp đen.
        </p>
        <ol className="steps">
          {STEPS.map(([Icon, title, text], i) => (
            <li key={title}>
              <span className="step-icon">
                <Icon />
              </span>
              <div>
                <strong>
                  {i + 1}. {title}
                </strong>
                <p>{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="panel landing-card">
        <div className="panel-head">
          <div>
            <h2>Xem tình hình học tập</h2>
            <p>Chọn trường và nhập mã sinh viên. Dữ liệu trong hệ thống là dữ liệu giả lập.</p>
          </div>
        </div>
        {universities.state === "error" && <ErrorBanner error={universities.error} onRetry={retry} />}
        <form onSubmit={submit} className="stack">
          <label>
            Trường
            <select value={chosenUni} disabled={universities.state !== "ok"} onChange={(e) => setUni(e.target.value)}>
              <option value="">{universities.state === "loading" ? "Đang tải…" : "Chọn trường"}</option>
              {universities.state === "ok" &&
                universities.data.map((u) => (
                  <option key={u.university_code} value={u.university_code}>
                    {u.name} ({u.university_code})
                  </option>
                ))}
            </select>
          </label>
          <label>
            Mã sinh viên
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Ví dụ 26000001"
              autoComplete="off"
              spellCheck={false}
              inputMode="numeric"
            />
          </label>
          <div className="samples">
            <span className="hint">Thử mã mẫu:</span>
            {SAMPLE_CODES.map((c) => (
              <button key={c} type="button" className="chip mono" onClick={() => setCode(c)}>
                {c}
              </button>
            ))}
          </div>
          <button type="submit" className="primary" disabled={!chosenUni || !code.trim()}>
            Xem
          </button>
        </form>
      </section>
    </div>
  );
}
