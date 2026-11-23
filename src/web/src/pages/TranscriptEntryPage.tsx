import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, type ApiClient } from "../api/client";
import type { CurriculumCourse, CurriculumDetail } from "../api/schema";
import type { Transcript } from "../api/transcript";
import { ErrorBanner } from "../components/ErrorBanner";
import { IconSearch } from "../components/Icons";
import { ProgressBar } from "../components/ProgressBar";
import { vn } from "../lib/format";
import {
  clampDraft,
  fieldTarget,
  fromBody,
  incompleteRows,
  loadDraft,
  prefill,
  saveDraft,
  toBody,
  type Draft,
  type DraftField,
  type DraftRow,
} from "../lib/transcriptDraft";
import { useApi, type Load } from "../lib/useApi";
import { MAX_SEMESTERS, choiceQuery, isComplete, readChoice } from "../lib/wizard";

type RowErrors = Record<string, Partial<Record<DraftField, string>>>;
type Summary =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "ok"; data: Transcript }
  | { state: "error"; error: unknown; other: [string, string][] };

const UNPLANNED = "Chưa xếp kỳ";

/**
 * Bước 4 (WEB-6, #39): tick môn đã học, nhập điểm hoặc "Miễn", chọn kỳ học, rồi "Xem tóm tắt"
 * gọi §6.10. Client không tính đạt/trượt hay GPA: chỉ cộng tín chỉ các môn đã tick để người dùng
 * biết mình đã chọn bao nhiêu trong khối tự chọn.
 */
export function TranscriptEntryPage({ client }: { client: ApiClient }) {
  const [params] = useSearchParams();
  const choice = readChoice(params);
  if (!isComplete(choice)) return <Navigate to={`/${choiceQuery(choice)}`} replace />;
  return (
    <TranscriptEntry
      key={`${choice.uni}/${choice.curriculum}`}
      client={client}
      uni={choice.uni}
      curriculum={choice.curriculum}
      semesters={choice.semesters!}
    />
  );
}

function TranscriptEntry({
  client,
  uni,
  curriculum,
  semesters,
}: {
  client: ApiClient;
  uni: string;
  curriculum: string;
  semesters: number;
}) {
  const [detail, retryDetail] = useApi((s) => client.curriculum(uni, curriculum, s), [client, uni, curriculum]);
  const [list, retryList] = useApi((s) => client.curriculumCourses(uni, curriculum, s), [client, uni, curriculum]);
  const courses = useMemo(() => (list.state === "ok" ? list.data.courses : []), [list]);

  const [draft, setDraft] = useState<Draft>(() => clampDraft(loadDraft(uni, curriculum), semesters));
  const [query, setQuery] = useState("");
  const [block, setBlock] = useState("");
  const [errors, setErrors] = useState<RowErrors>({});
  const [summary, setSummary] = useState<Summary>({ state: "idle" });
  const [fileError, setFileError] = useState("");
  const navigate = useNavigate();

  useEffect(() => saveDraft(uni, curriculum, semesters, draft), [uni, curriculum, semesters, draft]);

  const maxScore = detail.state === "ok" ? detail.data.max_score : undefined;
  const electives =
    detail.state === "ok" ? (detail.data.blocks ?? []).filter((b) => b.selection_rule === "choose_credits") : [];
  const blocksInList = useMemo(() => {
    const seen = new Map<string, string>();
    for (const c of courses) if (!seen.has(c.block_code)) seen.set(c.block_code, c.block_name);
    return [...seen];
  }, [courses]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return courses.filter(
      (c) =>
        (!block || c.block_code === block) &&
        (!q || c.course_code.toLowerCase().includes(q) || c.course_name.toLowerCase().includes(q)),
    );
  }, [courses, query, block]);
  const groups = useMemo(() => {
    const byTerm = new Map<string, CurriculumCourse[]>();
    for (const c of visible) {
      const label = c.recommended_semester ? `Kỳ ${c.recommended_semester}` : UNPLANNED;
      byTerm.set(label, [...(byTerm.get(label) ?? []), c]);
    }
    return [...byTerm].sort(([a], [b]) => order(a) - order(b));
  }, [visible]);

  const tickedCredits = courses.reduce((sum, c) => sum + (draft[c.course_code] ? c.credits : 0), 0);
  const tickedCount = Object.keys(draft).length;

  function change(next: Draft) {
    setDraft(next);
    setErrors({});
    if (summary.state !== "idle") setSummary({ state: "idle" });
  }
  function toggle(c: CurriculumCourse, on: boolean) {
    const next = { ...draft };
    if (on) {
      const planned = c.recommended_semester ?? semesters;
      next[c.course_code] = {
        semester: Math.min(Math.max(planned, 1), semesters),
        score: "",
        exempted: false,
      };
    } else delete next[c.course_code];
    change(next);
  }
  function edit(code: string, patch: Partial<DraftRow>) {
    change({ ...draft, [code]: { ...draft[code], ...patch } });
  }

  async function submit() {
    const missing = incompleteRows(draft);
    if (missing.length) {
      setErrors(Object.fromEntries(missing.map((code) => [code, { score: "Nhập điểm hoặc tick Miễn." }])));
      setSummary({ state: "idle" });
      document.getElementById(`row-${missing[0]}`)?.scrollIntoView?.({ block: "center" });
      return;
    }
    const { body, codes } = toBody(draft, courses, semesters);
    setErrors({});
    setSummary({ state: "loading" });
    try {
      setSummary({
        state: "ok",
        data: await client.transcript(uni, curriculum, body),
      });
    } catch (error) {
      const rowErrors: RowErrors = {};
      const other: [string, string][] = [];
      if (error instanceof ApiError) {
        for (const [path, message] of Object.entries(error.fieldErrors)) {
          const target = fieldTarget(path, codes);
          if (target)
            rowErrors[target.course] = {
              ...rowErrors[target.course],
              [target.field]: message,
            };
          else other.push([path, message]);
        }
      }
      setErrors(rowErrors);
      setSummary({ state: "error", error, other });
    }
  }

  const back = `/${choiceQuery({ uni, curriculum, semesters })}`;

  /** WEB-8: tải bảng điểm về máy, cùng dạng body §6.10. Dòng chưa có điểm và chưa "Miễn" không được ghi. */
  function exportFile() {
    const { body } = toBody(draft, courses, semesters);
    const url = URL.createObjectURL(new Blob([JSON.stringify(body, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `bang-diem-${curriculum}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  /** Đọc body §6.10, hoặc file mẫu trong test/fixtures/transcripts/ (body nằm trong `request`). */
  async function importFile(file: File) {
    let json: Record<string, unknown>;
    try {
      // FileReader thay cho file.text(): chạy được cả trên trình duyệt cũ và jsdom.
      const text = await new Promise<string>((ok, fail) => {
        const reader = new FileReader();
        reader.onload = () => ok(String(reader.result));
        reader.onerror = () => fail(reader.error);
        reader.readAsText(file);
      });
      json = JSON.parse(text);
    } catch {
      setFileError("File không phải JSON.");
      return;
    }
    if (typeof json?.curriculum_code === "string" && json.curriculum_code !== curriculum) {
      setFileError(`File là bảng điểm của khung ${json.curriculum_code}, không phải khung đang chọn.`);
      return;
    }
    const parsed = fromBody(json?.request ?? json);
    if (!parsed || !Number.isInteger(parsed.semesters) || parsed.semesters < 0 || parsed.semesters > MAX_SEMESTERS) {
      setFileError("File không đúng dạng bảng điểm: cần semesters_completed (0–12) và results.");
      return;
    }
    setFileError("");
    change(parsed.draft);
    if (parsed.semesters !== semesters)
      navigate(`/bang-diem${choiceQuery({ uni, curriculum, semesters: parsed.semesters })}`);
  }

  return (
    <div className="transcript">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Bước 4 · Nhập bảng điểm</h2>
            <p>
              {detail.state === "ok" ? detail.data.major_name : curriculum} · <span className="mono">{curriculum}</span>{" "}
              · đã học {semesters} kỳ
            </p>
          </div>
          <Link to={back} className="button-link">
            Sửa lựa chọn
          </Link>
        </div>
        <div className="row transcript-file">
          <label className="button-link">
            Nhập file JSON
            <input
              type="file"
              accept="application/json,.json"
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (file) void importFile(file);
              }}
            />
          </label>
          <button type="button" className="secondary" disabled={list.state !== "ok"} onClick={exportFile}>
            Xuất file JSON
          </button>
        </div>
        {fileError && (
          <p className="banner error" role="alert">
            {fileError}
          </p>
        )}
        {detail.state === "error" && <ErrorBanner error={detail.error} onRetry={retryDetail} />}
        {list.state === "error" && <ErrorBanner error={list.error} onRetry={retryList} />}
        {semesters === 0 ? (
          <p className="banner info">
            Bạn chưa học xong kỳ nào nên chưa có môn để nhập. Bấm "Xem tóm tắt" để xem lộ trình từ đầu.
          </p>
        ) : (
          <p className="hint">
            Tick các môn bạn đã học, nhập điểm lần học gần nhất (thang {maxScore !== undefined ? vn(maxScore, 1) : "…"})
            hoặc tick "Miễn". Môn học ở kỳ hè ghi vào kỳ chính ngay trước đó.
          </p>
        )}

        {semesters > 0 && (
          <div className="transcript-tools">
            <label className="search">
              <span className="sr-only">Tìm theo mã hoặc tên môn</span>
              <IconSearch />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Tìm theo mã hoặc tên môn"
              />
            </label>
            <label>
              <span className="sr-only">Lọc theo khối</span>
              <select aria-label="Lọc theo khối" value={block} onChange={(e) => setBlock(e.target.value)}>
                <option value="">Tất cả khối</option>
                {blocksInList.map(([code, name]) => (
                  <option key={code} value={code}>
                    {code} · {name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="secondary"
              disabled={list.state !== "ok"}
              onClick={() => change(prefill(draft, courses, semesters))}
            >
              Điền sẵn các môn kỳ 1..{semesters}
            </button>
            <button type="button" className="ghost" disabled={tickedCount === 0} onClick={() => change({})}>
              Bỏ tick tất cả
            </button>
          </div>
        )}

        {semesters > 0 && electives.length > 0 && (
          <ul className="elective-progress" aria-label="Khối tự chọn">
            {electives.map((b) => {
              const chosen = courses.reduce(
                (sum, c) => sum + (c.block_code === b.block_code && draft[c.course_code] ? c.credits : 0),
                0,
              );
              return (
                <li key={b.block_code}>
                  <span>
                    <span className="mono">{b.block_code}</span> {b.block_name}
                  </span>
                  <span>
                    đã chọn {chosen} / cần {b.required_credits} tín chỉ
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {semesters > 0 && list.state === "loading" && <p className="muted">Đang tải danh sách môn…</p>}
      {semesters > 0 && list.state === "ok" && courses.length === 0 && (
        <p className="muted">Khung này chưa có học phần nào.</p>
      )}
      {semesters > 0 && list.state === "ok" && courses.length > 0 && visible.length === 0 && (
        <p className="muted">Không có môn nào khớp bộ lọc.</p>
      )}

      {semesters > 0 &&
        groups.map(([label, items]) => (
          <section key={label} className="panel transcript-group" aria-label={label}>
            <h3>{label === UNPLANNED ? label : `${label} dự kiến`}</h3>
            <ul className="course-rows">
              {items.map((c) => (
                <CourseRow
                  key={c.course_code}
                  course={c}
                  row={draft[c.course_code]}
                  errors={errors[c.course_code]}
                  semesters={semesters}
                  maxScore={maxScore}
                  onToggle={(on) => toggle(c, on)}
                  onEdit={(patch) => edit(c.course_code, patch)}
                />
              ))}
            </ul>
          </section>
        ))}

      <div className="transcript-bar">
        <span>
          Đã tick <strong>{tickedCount}</strong> môn · <strong>{tickedCredits}</strong> tín chỉ
        </span>
        <button
          type="button"
          className="primary"
          disabled={summary.state === "loading" || (semesters > 0 && list.state !== "ok")}
          onClick={submit}
        >
          {summary.state === "loading" ? "Đang tính…" : "Xem tóm tắt"}
        </button>
      </div>

      {Object.keys(errors).length > 0 && summary.state === "idle" && (
        <p className="banner error" role="alert">
          Còn {Object.keys(errors).length} môn đã tick chưa có điểm. Nhập điểm hoặc tick "Miễn" ở các ô được đánh dấu.
        </p>
      )}
      {summary.state === "error" && (
        <>
          <ErrorBanner error={summary.error} onRetry={submit} />
          {summary.other.length > 0 && (
            <ul className="banner error">
              {summary.other.map(([path, message]) => (
                <li key={path}>
                  <span className="mono">{path}</span>: {message}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {summary.state === "ok" && (
        <TranscriptSummary
          data={summary.data}
          courses={courses}
          detail={detail}
          next={`/goi-y${choiceQuery({ uni, curriculum, semesters })}`}
        />
      )}
    </div>
  );
}

/** "Kỳ 2" → 2; "Chưa xếp kỳ" xuống cuối. */
function order(label: string): number {
  const n = Number(label.replace(/\D/g, ""));
  return label === UNPLANNED ? Number.MAX_SAFE_INTEGER : n;
}

function CourseRow({
  course: c,
  row,
  errors,
  semesters,
  maxScore,
  onToggle,
  onEdit,
}: {
  course: CurriculumCourse;
  row: DraftRow | undefined;
  errors: Partial<Record<DraftField, string>> | undefined;
  semesters: number;
  maxScore: number | undefined;
  onToggle: (on: boolean) => void;
  onEdit: (patch: Partial<DraftRow>) => void;
}) {
  const id = `row-${c.course_code}`;
  const invalid = errors && Object.keys(errors).length > 0;
  return (
    <li id={id} className={`course-row${row ? " ticked" : ""}${invalid ? " invalid" : ""}`}>
      <label className="course-pick">
        <input type="checkbox" checked={Boolean(row)} onChange={(e) => onToggle(e.target.checked)} />
        <span>
          <strong>{c.course_name}</strong>
          <span className="course-meta">
            <span className="mono">{c.course_code}</span> · {c.credits} tín chỉ · khối {c.block_code}
            {!c.is_required && " · tự chọn"}
          </span>
        </span>
      </label>
      {row && (
        <div className="course-inputs">
          <label>
            Điểm
            <input
              type="number"
              inputMode="decimal"
              min={0}
              max={maxScore}
              step={0.1}
              value={row.score}
              disabled={row.exempted}
              aria-label={`Điểm ${c.course_code}`}
              aria-invalid={Boolean(errors?.score) || undefined}
              onChange={(e) => onEdit({ score: e.target.value })}
            />
          </label>
          <label className="inline-check">
            <input
              type="checkbox"
              checked={row.exempted}
              aria-label={`Miễn ${c.course_code}`}
              onChange={(e) =>
                onEdit({
                  exempted: e.target.checked,
                  score: e.target.checked ? "" : row.score,
                })
              }
            />
            Miễn
          </label>
          <label>
            Kỳ học
            <select
              value={row.semester}
              aria-label={`Kỳ học ${c.course_code}`}
              aria-invalid={Boolean(errors?.semester) || undefined}
              onChange={(e) => onEdit({ semester: Number(e.target.value) })}
            >
              {Array.from({ length: semesters }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  Kỳ {n}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {invalid && (
        <ul className="row-errors" role="alert">
          {Object.entries(errors!).map(([field, message]) => (
            <li key={field}>{message}</li>
          ))}
        </ul>
      )}
    </li>
  );
}

function TranscriptSummary({
  data: t,
  courses,
  detail,
  next,
}: {
  data: Transcript;
  courses: CurriculumCourse[];
  detail: Load<CurriculumDetail>;
  /** Bước 5: gợi ý kỳ tới (§6.11), dùng cùng bản nháp. */
  next: string;
}) {
  const { warnings = [], outstanding_courses = [], blocks = [] } = t;
  const names = new Map(courses.map((c) => [c.course_code, c.course_name]));
  for (const c of t.courses) names.set(c.course_code, c.course_name);
  const blockNames = new Map(
    detail.state === "ok" ? (detail.data.blocks ?? []).map((b) => [b.block_code, b.block_name]) : [],
  );
  return (
    <section className="panel transcript-summary" aria-labelledby="summary-title">
      <div className="panel-head">
        <h2 id="summary-title">Tóm tắt bảng điểm</h2>
        <p>Kỳ tới là kỳ {t.target_semester} của bạn.</p>
        <Link to={next} className="button-link">
          Xem gợi ý cho kỳ {t.target_semester}
        </Link>
      </div>
      <dl className="stat-grid">
        <div className="stat">
          <dt>Tín chỉ tích lũy</dt>
          <dd>
            {t.credits_earned} / {t.total_credits}
          </dd>
          <ProgressBar value={t.credits_earned} max={t.total_credits} label="Tín chỉ tích lũy" />
        </div>
        <div className="stat">
          <dt>Điểm trung bình (thang 4)</dt>
          <dd>{t.gpa == null ? <span className="muted">Chưa có điểm</span> : vn(t.gpa)}</dd>
        </div>
        <div className={`stat ${t.credits_outstanding > 0 ? "stat-warn" : ""}`}>
          <dt>Tín chỉ đang nợ</dt>
          <dd>{t.credits_outstanding}</dd>
        </div>
        <div className="stat">
          <dt>Môn đã đạt</dt>
          <dd>{t.summary.passed}</dd>
        </div>
      </dl>

      {warnings.length > 0 && (
        <div className="banner warn">
          <strong>Kiểm tra lại</strong>
          <ul>
            {warnings.map((w, i) => (
              <li key={`${w.code}-${w.course_code ?? i}`}>{w.text}</li>
            ))}
          </ul>
        </div>
      )}

      <h3>Môn đang nợ</h3>
      {outstanding_courses.length === 0 ? (
        <p className="muted">Không có môn nào đang nợ.</p>
      ) : (
        <ul className="chips chips-warn">
          {outstanding_courses.map((code) => (
            <li key={code}>
              <span className="mono">{code}</span> {names.get(code)}
            </li>
          ))}
        </ul>
      )}

      <h3>Tiến độ theo khối</h3>
      <ul className="block-progress">
        {blocks.map((b) => (
          <li key={b.block_code}>
            <span>
              <span className="mono">{b.block_code}</span> {blockNames.get(b.block_code)}
            </span>
            <span>
              {b.earned_credits} / {b.required_credits} tín chỉ
            </span>
            <ProgressBar value={b.earned_credits} max={b.required_credits} label={`Khối ${b.block_code}`} />
          </li>
        ))}
      </ul>

      {t.courses.length > 0 && (
        <>
          <h3>Nhận xét từng môn</h3>
          <ul className="course-texts">
            {t.courses.map((c) => (
              <li key={c.course_code} className={`status-${c.status}`}>
                {c.text}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
