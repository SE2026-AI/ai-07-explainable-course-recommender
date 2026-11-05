import { useMemo, useState, type FormEvent } from "react";
import { ApiError } from "../../api/errors";
import {
  WEIGHT_KEYS,
  type Assumption,
  type CourseStatusItem,
  type RecommendationBody,
  type Recommendations,
  type Swap,
  type WeightKey,
} from "../../api/schema";
import { ErrorBanner } from "../../components/ErrorBanner";
import { IconCheck, IconPlus, IconSearch, IconSliders } from "../../components/Icons";
import { Prerequisites } from "../../components/Prerequisites";
import { ReasonList, ScoreCheck, reasonLabel } from "../../components/ReasonList";
import { vn } from "../../lib/format";
import { usePlan } from "../../lib/plan";
import { StatusBadge, statusLabel } from "../../lib/status";
import { useApi } from "../../lib/useApi";
import { useStudent } from "./StudentLayout";

type Weights = Record<WeightKey, number>;
interface AssumptionDraft {
  course_code: string;
  status: "passed" | "failed";
  score: string;
}

/**
 * Màn hình trung tâm (§6.6): danh sách gợi ý, bảng giải thích, điều chỉnh trọng số và what-if.
 * Mọi con số đến từ server; client chỉ gửi yêu cầu và hiện kết quả, không tính điểm hay thứ hạng.
 */
export function RecommendationsPage() {
  const { client, ref, term } = useStudent();
  // null: GET với trọng số mặc định. Khác null: POST với body này.
  const [body, setBody] = useState<RecommendationBody | null>(null);
  const [result, retry] = useApi(
    (s) => (body ? client.recommend(ref, body, s) : client.recommendations(ref, { term }, s)),
    [client, ref.uni, ref.student, term, JSON.stringify(body)],
  );
  const [status] = useApi((s) => client.courseStatus(ref, { term }, s), [client, ref.uni, ref.student, term]);
  const courses = status.state === "ok" ? status.data.courses : [];

  const [limit, setLimit] = useState("5");
  const [weights, setWeights] = useState<Weights | null>(null);
  const [assumptions, setAssumptions] = useState<AssumptionDraft[]>([]);
  const [skip, setSkip] = useState<string[]>([]);
  const [swap, setSwap] = useState<Swap[]>([]);

  const shownWeights: Weights | null = weights ?? (result.state === "ok" ? (result.data.weights as Weights) : null);

  function apply(e?: FormEvent) {
    e?.preventDefault();
    const next: RecommendationBody = {
      limit: Number(limit),
      assumptions: assumptions
        .filter((a) => a.course_code)
        .map(
          (a): Assumption => ({
            course_code: a.course_code,
            status: a.status,
            ...(a.score.trim() === "" ? {} : { score: Number(a.score.replace(",", ".")) }),
          }),
        ),
      skip,
      swap: swap.filter((p) => p.course_code && p.replacement),
    };
    if (term) next.term = term;
    if (weights) next.weights = weights;
    setBody(next);
  }

  function reset() {
    setLimit("5");
    setWeights(null);
    setAssumptions([]);
    setSkip([]);
    setSwap([]);
    setBody(null);
  }

  return (
    <div className="split">
      <form className="panel controls sticky" onSubmit={apply}>
        <div className="controls-head">
          <IconSliders />
          <div>
            <h2>Điều chỉnh</h2>
            <p className="hint">Đổi trọng số hoặc thử giả định rồi bấm Áp dụng.</p>
          </div>
        </div>
        <label>
          Số gợi ý (tối đa 20)
          <input type="number" min={1} value={limit} onChange={(e) => setLimit(e.target.value)} />
        </label>
        <fieldset>
          <legend>Trọng số</legend>
          {shownWeights ? (
            WEIGHT_KEYS.map((k) => (
              <label key={k} className="slider">
                <span>
                  {reasonLabel(k)} <span className="mono">{vn(shownWeights[k] ?? 0, 2)}</span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={5}
                  step={0.25}
                  value={shownWeights[k] ?? 0}
                  onChange={(e) => setWeights({ ...shownWeights, [k]: Number(e.target.value) })}
                />
              </label>
            ))
          ) : (
            <p className="hint">Đang tải trọng số…</p>
          )}
        </fieldset>
        <WhatIf
          courses={courses}
          assumptions={assumptions}
          setAssumptions={setAssumptions}
          skip={skip}
          setSkip={setSkip}
          swap={swap}
          setSwap={setSwap}
        />
        <div className="row controls-actions">
          <button type="submit" className="primary">
            Áp dụng
          </button>
          <button type="button" className="secondary" onClick={reset}>
            Về mặc định
          </button>
        </div>
      </form>

      <div className="results">
        {result.state === "loading" && (
          <div className="panel skeleton-list" role="status">
            <span className="sr-only">Đang tải gợi ý…</span>
            <span />
            <span />
            <span />
          </div>
        )}
        {result.state === "error" && <RecommendError error={result.error} onRetry={retry} />}
        {result.state === "ok" && (
          <Results
            data={result.data}
            onSkip={(code) => setSkip((cur) => (cur.includes(code) ? cur : [...cur, code]))}
          />
        )}
      </div>
    </div>
  );
}

function RecommendError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const fields = error instanceof ApiError ? Object.entries(error.fieldErrors) : [];
  return (
    <>
      <ErrorBanner error={error} onRetry={fields.length ? undefined : onRetry} />
      {fields.length > 0 && (
        <ul className="field-errors" aria-label="Trường bị lỗi">
          {fields.map(([field, msg]) => (
            <li key={field}>
              <span className="mono">{field}</span>: {msg}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Results({ data, onSkip }: { data: Recommendations; onSkip: (code: string) => void }) {
  const plan = usePlan();
  const items = data.items ?? [];
  const groups = useMemo(() => {
    const notEligible = data.not_eligible ?? [];
    const m = new Map<string, CourseStatusItem[]>();
    for (const c of notEligible) m.set(c.status, [...(m.get(c.status) ?? []), c]);
    return [...m.entries()];
  }, [data.not_eligible]);
  const notEligible = data.not_eligible ?? [];
  const [whyFilter, setWhyFilter] = useState("");
  const needle = whyFilter.trim().toLowerCase();
  const totalCredits = items.reduce((t, it) => t + it.credits, 0);
  const missing = items.filter((it) => !plan.codes.includes(it.course_code));

  return (
    <>
      {data.what_if && (
        <p className="banner warn" role="status">
          <span>
            Đang xem <strong>kịch bản giả định</strong>. Kết quả học tập thật của bạn không bị thay đổi.
          </span>
        </p>
      )}
      <section className="panel">
        <div className="panel-head">
          <h2>Gợi ý cho học kỳ {data.term}</h2>
          <p>
            {items.length} / {data.candidate_count} môn có thể học · thuật toán {data.algorithm_version}
          </p>
        </div>
        {items.length > 0 && (
          <div className="rec-summary">
            <span>
              Tổng <strong>{totalCredits}</strong> tín chỉ nếu học cả {items.length} môn
            </span>
            <button
              type="button"
              className="secondary small"
              disabled={missing.length === 0}
              onClick={() => missing.forEach((it) => plan.add(it.course_code))}
            >
              {missing.length === 0 ? <IconCheck /> : <IconPlus />}
              {missing.length === 0 ? "Đã thêm hết vào kế hoạch" : "Thêm tất cả vào kế hoạch"}
            </button>
          </div>
        )}
        {items.length === 0 ? (
          <p className="muted">Không có môn nào để gợi ý ở học kỳ này.</p>
        ) : (
          // Giữ đúng thứ tự server trả về: thứ tự là một phần của hợp đồng (§3.3).
          <ol className="recs">
            {items.map((it) => {
              const inPlan = plan.codes.includes(it.course_code);
              return (
                <li key={it.course_code} className="rec">
                  <div className="rec-head">
                    <span className="rank">{it.rank}</span>
                    <div className="rec-title">
                      <strong>{it.course_name}</strong> <span className="mono muted">{it.course_code}</span>
                      <div className="hint">
                        {it.credits} tín chỉ · khối {it.block_code} · <StatusBadge status={it.status} />
                      </div>
                    </div>
                    <div className="score-box">
                      <span className="score">{vn(it.score, 4)}</span>
                      <ScoreCheck reasons={it.reasons ?? []} score={it.score} />
                    </div>
                  </div>
                  <ReasonList reasons={it.reasons ?? []} score={it.score} />
                  <div className="row">
                    <button
                      type="button"
                      className={`small ${inPlan ? "in-plan" : "secondary"}`}
                      aria-pressed={inPlan}
                      onClick={() => (inPlan ? plan.remove(it.course_code) : plan.add(it.course_code))}
                    >
                      {inPlan ? <IconCheck /> : <IconPlus />}
                      {inPlan ? "Trong kế hoạch" : "Thêm vào kế hoạch"}
                    </button>
                    <button type="button" className="ghost small" onClick={() => onSkip(it.course_code)}>
                      Chưa học kỳ này
                    </button>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
        <details className="weights-used">
          <summary>Trọng số server đã dùng</summary>
          <table className="table">
            <tbody>
              {Object.entries(data.weights).map(([k, v]) => (
                <tr key={k}>
                  <td>{reasonLabel(k)}</td>
                  <td className="mono">{k}</td>
                  <td className="mono">{vn(Number(v), 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </section>

      {/* "Vì sao chưa" lấy từ not_eligible của cùng phản hồi; hợp đồng không có endpoint riêng. */}
      <section className="panel">
        <div className="panel-head">
          <h2>Vì sao chưa gợi ý các môn còn lại</h2>
          <p>{notEligible.length} học phần</p>
        </div>
        <p className="hint">
          Các môn dưới đây chưa vào danh sách gợi ý. Mở từng nhóm để xem lý do, hoặc tìm một môn cụ thể.
        </p>
        {notEligible.length > 8 && (
          <label className="search">
            <IconSearch />
            <input
              type="search"
              aria-label="Tìm môn chưa được gợi ý"
              value={whyFilter}
              onChange={(e) => setWhyFilter(e.target.value)}
              placeholder="Tìm theo mã hoặc tên môn"
            />
          </label>
        )}
        {groups.map(([s, all]) => {
          const list = needle
            ? all.filter((c) => `${c.course_code} ${c.course_name}`.toLowerCase().includes(needle))
            : all;
          if (list.length === 0) return null;
          return (
            <details key={s} className="why-group" open={!!needle || all.length <= 8}>
              <summary>
                {statusLabel(s)} <span className="count">{list.length}</span>
              </summary>
              <ul className="course-list compact">
                {list.map((c) => (
                  <li key={c.course_code}>
                    <span className="mono">{c.course_code}</span> {c.text ?? c.course_name}
                    {c.missing_prerequisites && c.missing_prerequisites.length > 0 && (
                      <span className="hint">
                        {" "}
                        · còn thiếu <Prerequisites groups={c.missing_prerequisites} />
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          );
        })}
      </section>
    </>
  );
}

function WhatIf(props: {
  courses: CourseStatusItem[];
  assumptions: AssumptionDraft[];
  setAssumptions: (a: AssumptionDraft[]) => void;
  skip: string[];
  setSkip: (s: string[]) => void;
  swap: Swap[];
  setSwap: (s: Swap[]) => void;
}) {
  const { courses, assumptions, setAssumptions, skip, setSkip, swap, setSwap } = props;
  const name = (code: string) => courses.find((c) => c.course_code === code)?.course_name ?? code;
  // skip/swap chỉ nhận môn retake/eligible (§6.6). Danh sách lấy theo course-status hiện tại;
  // nếu giả định làm đổi trạng thái thì server vẫn là nơi quyết định và sẽ trả validation_error.
  const candidates = courses.filter((c) => c.status === "retake" || c.status === "eligible");
  const options = (list: CourseStatusItem[]) =>
    list.map((c) => (
      <option key={c.course_code} value={c.course_code}>
        {c.course_code} · {c.course_name}
      </option>
    ));

  return (
    <fieldset className="whatif">
      <legend>Giả định what-if</legend>
      <p className="hint">Chỉ áp lên bản sao trong bộ nhớ của server; không ghi vào dữ liệu thật.</p>

      <h4>Giả định kết quả một môn</h4>
      {assumptions.map((a, i) => {
        const set = (patch: Partial<AssumptionDraft>) =>
          setAssumptions(assumptions.map((x, j) => (j === i ? { ...x, ...patch } : x)));
        return (
          <div key={i} className="whatif-row">
            <select
              aria-label="Môn giả định"
              value={a.course_code}
              onChange={(e) => set({ course_code: e.target.value })}
            >
              <option value="">Chọn môn</option>
              {options(courses)}
            </select>
            <select
              aria-label="Kết quả giả định"
              value={a.status}
              onChange={(e) => set({ status: e.target.value as AssumptionDraft["status"] })}
            >
              <option value="passed">đạt</option>
              <option value="failed">không đạt</option>
            </select>
            <input
              aria-label="Điểm giả định"
              placeholder="điểm"
              value={a.score}
              onChange={(e) => set({ score: e.target.value })}
            />
            <button
              type="button"
              className="icon"
              aria-label="Bỏ giả định"
              onClick={() => setAssumptions(assumptions.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </div>
        );
      })}
      <button
        type="button"
        className="dashed"
        onClick={() => setAssumptions([...assumptions, { course_code: "", status: "passed", score: "" }])}
      >
        + Thêm giả định
      </button>

      <h4>Chưa muốn học ở học kỳ này</h4>
      {skip.length > 0 && (
        <ul className="chips">
          {skip.map((c) => (
            <li key={c}>
              {name(c)}{" "}
              <button
                type="button"
                className="icon"
                aria-label={`Bỏ ${c}`}
                onClick={() => setSkip(skip.filter((x) => x !== c))}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <select
        aria-label="Thêm môn chưa muốn học"
        value=""
        onChange={(e) => e.target.value && setSkip([...skip, e.target.value])}
      >
        <option value="">Chọn môn</option>
        {options(candidates.filter((c) => !skip.includes(c.course_code)))}
      </select>

      <h4>Đổi môn lấy môn khác</h4>
      {swap.map((p, i) => {
        const set = (patch: Partial<Swap>) => setSwap(swap.map((x, j) => (j === i ? { ...x, ...patch } : x)));
        return (
          <div key={i} className="whatif-row">
            <select aria-label="Môn bỏ" value={p.course_code} onChange={(e) => set({ course_code: e.target.value })}>
              <option value="">Bỏ môn</option>
              {options(candidates)}
            </select>
            <span>→</span>
            <select aria-label="Môn thay" value={p.replacement} onChange={(e) => set({ replacement: e.target.value })}>
              <option value="">Thay bằng</option>
              {options(candidates)}
            </select>
            <button
              type="button"
              className="icon"
              aria-label="Bỏ cặp đổi"
              onClick={() => setSwap(swap.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </div>
        );
      })}
      <button type="button" className="dashed" onClick={() => setSwap([...swap, { course_code: "", replacement: "" }])}>
        + Thêm cặp đổi
      </button>
    </fieldset>
  );
}
