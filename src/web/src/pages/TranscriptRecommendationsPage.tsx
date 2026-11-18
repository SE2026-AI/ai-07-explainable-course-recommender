import { useMemo, useState, type FormEvent } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { ApiError, type ApiClient } from "../api/client";
import { WEIGHT_KEYS } from "../api/schema";
import type {
  NotSelected,
  TranscriptRecommendationBody,
  TranscriptRecommendations,
} from "../api/transcript";
import { ErrorBanner } from "../components/ErrorBanner";
import { IconSliders } from "../components/Icons";
import { Prerequisites } from "../components/Prerequisites";
import { ReasonList, ScoreCheck, reasonLabel } from "../components/ReasonList";
import { vn } from "../lib/format";
import { StatusBadge } from "../lib/status";
import {
  clampDraft,
  fieldTarget,
  loadDraft,
  toBody,
} from "../lib/transcriptDraft";
import { useApi } from "../lib/useApi";
import { choiceQuery, isComplete, readChoice } from "../lib/wizard";

/** Phần body ngoài bảng điểm: những gì người dùng chỉnh trên màn này. */
type Options = Omit<
  TranscriptRecommendationBody,
  "semesters_completed" | "results"
> & {
  skip: string[];
  include: string[];
};

/** §6.11 quy định 10: v1 không bao giờ trả lý do `interest` ở endpoint này, nên không cho chỉnh. */
const WEIGHTS = WEIGHT_KEYS.filter((k) => k !== "interest");

const NOT_SELECTED_LABEL: Record<string, string> = {
  skipped: "Bạn chọn chưa học kỳ này",
  block_full: "Khối tự chọn đã đủ tín chỉ",
  credit_budget: "Vượt số tín chỉ tối đa",
};

/**
 * Bước 5 (WEB-7, #39): gợi ý kỳ kế tiếp cho bảng điểm tự nhập (§6.11). Bảng điểm lấy từ bản nháp
 * của bước 4; màn này chỉ thêm khoảng tín chỉ, trọng số, `skip` và `include`. Mọi thứ hạng, điểm,
 * lý do và câu chữ đến từ server.
 */
export function TranscriptRecommendationsPage({
  client,
}: {
  client: ApiClient;
}) {
  const [params] = useSearchParams();
  const choice = readChoice(params);
  if (!isComplete(choice))
    return <Navigate to={`/${choiceQuery(choice)}`} replace />;
  return (
    <TranscriptRecs
      key={`${choice.uni}/${choice.curriculum}/${choice.semesters}`}
      client={client}
      uni={choice.uni}
      curriculum={choice.curriculum}
      semesters={choice.semesters!}
    />
  );
}

function TranscriptRecs({
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
  const [list, retryList] = useApi(
    (s) => client.curriculumCourses(uni, curriculum, s),
    [client, uni, curriculum],
  );
  // shortcut: dòng đã tick mà chưa có điểm bị toBody bỏ qua; bước 4 chặn trường hợp này trước khi dẫn sang đây.
  const transcript = useMemo(
    () =>
      list.state === "ok"
        ? toBody(
            clampDraft(loadDraft(uni, curriculum), semesters),
            list.data.courses,
            semesters,
          )
        : null,
    [list, uni, curriculum, semesters],
  );

  const [opts, setOpts] = useState<Options>({ skip: [], include: [] });
  const [result, retry] = useApi(
    transcript
      ? (s) =>
          client.recommendTranscript(
            uni,
            curriculum,
            { ...transcript.body, ...opts },
            s,
          )
      : null,
    [client, uni, curriculum, transcript, JSON.stringify(opts)],
  );

  const [minCredits, setMinCredits] = useState("");
  const [maxCredits, setMaxCredits] = useState("");
  const [weights, setWeights] = useState<Record<string, number> | null>(null);
  const shownWeights =
    weights ?? (result.state === "ok" ? result.data.weights : null);

  function apply(e: FormEvent) {
    e.preventDefault();
    setOpts(({ skip, include }) => ({
      skip,
      include,
      ...(minCredits.trim() ? { min_credits: Number(minCredits) } : {}),
      ...(maxCredits.trim() ? { max_credits: Number(maxCredits) } : {}),
      ...(weights ? { weights } : {}),
    }));
  }
  function reset() {
    setMinCredits("");
    setMaxCredits("");
    setWeights(null);
    setOpts({ skip: [], include: [] });
  }
  // Một mã chỉ nằm ở một trong hai danh sách (§6.11), nên chuyển sang danh sách này thì bỏ khỏi danh sách kia.
  const without = (o: Options, code: string) => ({
    ...o,
    skip: o.skip.filter((c) => c !== code),
    include: o.include.filter((c) => c !== code),
  });
  const skip = (code: string) =>
    setOpts((o) => ({
      ...without(o, code),
      skip: [...without(o, code).skip, code],
    }));
  const include = (code: string) =>
    setOpts((o) => ({
      ...without(o, code),
      include: [...without(o, code).include, code],
    }));
  const unset = (code: string) => setOpts((o) => without(o, code));

  const names = new Map(
    list.state === "ok"
      ? list.data.courses.map((c) => [c.course_code, c.course_name])
      : [],
  );
  const query = choiceQuery({ uni, curriculum, semesters });

  return (
    <div className="transcript">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Bước 5 · Gợi ý kỳ tới</h2>
            <p>
              <span className="mono">{curriculum}</span> · đã học {semesters} kỳ
              {transcript &&
                ` · ${transcript.body.results.length} môn trong bảng điểm`}
            </p>
          </div>
          <Link to={`/bang-diem${query}`} className="button-link">
            Quay lại sửa bảng điểm
          </Link>
        </div>
        {list.state === "error" && (
          <ErrorBanner error={list.error} onRetry={retryList} />
        )}
      </section>

      <div className="split">
        <form className="panel controls sticky" onSubmit={apply}>
          <div className="controls-head">
            <IconSliders />
            <div>
              <h2>Điều chỉnh</h2>
              <p className="hint">
                Đổi khoảng tín chỉ hoặc trọng số rồi bấm Áp dụng.
              </p>
            </div>
          </div>
          <label>
            Tín chỉ tối thiểu (từ 10)
            <input
              type="number"
              min={10}
              placeholder="10"
              value={minCredits}
              onChange={(e) => setMinCredits(e.target.value)}
            />
          </label>
          <label>
            Tín chỉ tối đa
            <input
              type="number"
              min={10}
              placeholder="20"
              value={maxCredits}
              onChange={(e) => setMaxCredits(e.target.value)}
            />
          </label>
          <fieldset>
            <legend>Trọng số</legend>
            {shownWeights ? (
              WEIGHTS.map((k) => (
                <label key={k} className="slider">
                  <span>
                    {reasonLabel(k)}{" "}
                    <span className="mono">{vn(shownWeights[k] ?? 0, 2)}</span>
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={5}
                    step={0.25}
                    value={shownWeights[k] ?? 0}
                    onChange={(e) =>
                      setWeights({
                        ...shownWeights,
                        [k]: Number(e.target.value),
                      })
                    }
                  />
                </label>
              ))
            ) : (
              <p className="hint">Đang tải trọng số…</p>
            )}
          </fieldset>
          <Chosen
            title="Chưa học kỳ này"
            codes={opts.skip}
            names={names}
            onRemove={unset}
          />
          <Chosen
            title="Chắc chắn học kỳ này"
            codes={opts.include}
            names={names}
            onRemove={unset}
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
          {(result.state === "loading" || result.state === "idle") &&
            list.state !== "error" && (
              <div className="panel skeleton-list" role="status">
                <span className="sr-only">Đang tải gợi ý…</span>
                <span />
                <span />
                <span />
              </div>
            )}
          {result.state === "error" && (
            <RecsError
              error={result.error}
              codes={transcript?.codes ?? []}
              opts={opts}
              onRetry={retry}
              back={query}
            />
          )}
          {result.state === "ok" && (
            <Results
              data={result.data}
              include={opts.include}
              onSkip={skip}
              onInclude={include}
              onUnset={unset}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function Chosen({
  title,
  codes,
  names,
  onRemove,
}: {
  title: string;
  codes: string[];
  names: Map<string, string>;
  onRemove: (code: string) => void;
}) {
  if (codes.length === 0) return null;
  return (
    <>
      <h4>{title}</h4>
      <ul className="chips">
        {codes.map((c) => (
          <li key={c}>
            {names.get(c) ?? c}{" "}
            <button
              type="button"
              className="icon"
              aria-label={`Bỏ ${c}`}
              onClick={() => onRemove(c)}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

/** 422: `results[i]` đổi về mã môn của bảng điểm, `skip[i]`/`include[i]` về mã đã chọn trên màn này. */
function RecsError({
  error,
  codes,
  opts,
  onRetry,
  back,
}: {
  error: unknown;
  codes: string[];
  opts: Options;
  onRetry: () => void;
  back: string;
}) {
  const fields =
    error instanceof ApiError ? Object.entries(error.fieldErrors) : [];
  const label = (path: string) => {
    const row = fieldTarget(path, codes);
    if (row) return `bảng điểm, môn ${row.course}`;
    const m = /^(skip|include)\[(\d+)\]$/.exec(path);
    const code = m && opts[m[1] as "skip" | "include"][Number(m[2])];
    return code
      ? `${m![1] === "skip" ? "chưa học kỳ này" : "chắc chắn học"}: ${code}`
      : path;
  };
  const inTranscript = fields.some(([path]) => fieldTarget(path, codes));
  return (
    <>
      <ErrorBanner
        error={error}
        onRetry={fields.length ? undefined : onRetry}
      />
      {fields.length > 0 && (
        <ul className="field-errors" aria-label="Trường bị lỗi">
          {fields.map(([path, msg]) => (
            <li key={path}>
              <span className="mono">{label(path)}</span>: {msg}
            </li>
          ))}
        </ul>
      )}
      {inTranscript && (
        <Link to={`/bang-diem${back}`} className="button-link">
          Sửa bảng điểm
        </Link>
      )}
    </>
  );
}

function Results({
  data,
  include,
  onSkip,
  onInclude,
  onUnset,
}: {
  data: TranscriptRecommendations;
  include: string[];
  onSkip: (code: string) => void;
  onInclude: (code: string) => void;
  onUnset: (code: string) => void;
}) {
  const groups = useMemo(() => {
    const m = new Map<string, NotSelected[]>();
    for (const c of data.not_selected)
      m.set(c.reason, [...(m.get(c.reason) ?? []), c]);
    return [...m];
  }, [data.not_selected]);

  return (
    <>
      {data.what_if && (
        <p className="banner warn" role="status">
          Đang xem <strong>kịch bản giả định</strong> với các môn bạn chọn học
          hoặc chưa học. Bảng điểm không bị thay đổi.
        </p>
      )}
      {data.warnings.length > 0 && (
        <div className="banner warn">
          <strong>Kiểm tra lại</strong>
          <ul>
            {data.warnings.map((w, i) => (
              <li key={`${w.code}-${w.course_code ?? i}`}>{w.text}</li>
            ))}
          </ul>
        </div>
      )}

      <section className="panel">
        <div className="panel-head">
          <h2>Gợi ý cho kỳ {data.target_semester}</h2>
          <p>
            {data.items.length} / {data.candidate_count} môn học được · thuật
            toán {data.algorithm_version}
          </p>
        </div>
        <p className="rec-summary" data-testid="credit-window">
          {data.credit_window.text}
        </p>
        {data.items.length === 0 ? (
          <p className="muted">Không có môn nào để gợi ý ở kỳ này.</p>
        ) : (
          // Giữ đúng thứ tự server trả về (§3.3).
          <ol className="recs">
            {data.items.map((it) => (
              <li key={it.course_code} className="rec">
                <div className="rec-head">
                  <span className="rank">{it.rank}</span>
                  <div className="rec-title">
                    <strong>{it.course_name}</strong>{" "}
                    <span className="mono muted">{it.course_code}</span>
                    <div className="hint">
                      {it.credits} tín chỉ · khối {it.block_code} ·{" "}
                      <StatusBadge status={it.status} />
                      {include.includes(it.course_code) && " · bạn chọn học"}
                    </div>
                  </div>
                  <div className="score-box">
                    <span className="score">{vn(it.score, 4)}</span>
                    <ScoreCheck reasons={it.reasons ?? []} score={it.score} />
                  </div>
                </div>
                <ReasonList reasons={it.reasons ?? []} score={it.score} />
                <div className="row">
                  {include.includes(it.course_code) ? (
                    <button
                      type="button"
                      className="ghost small"
                      onClick={() => onUnset(it.course_code)}
                    >
                      Bỏ chọn học
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="ghost small"
                      onClick={() => onSkip(it.course_code)}
                    >
                      Chưa học kỳ này
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Học được nhưng chưa xếp</h2>
          <p>{data.not_selected.length} học phần</p>
        </div>
        {data.not_selected.length === 0 && (
          <p className="muted">Mọi môn học được đều đã vào danh sách gợi ý.</p>
        )}
        {groups.map(([reason, list]) => (
          <details key={reason} className="why-group" open>
            <summary>
              {NOT_SELECTED_LABEL[reason] ?? reason}{" "}
              <span className="count">{list.length}</span>
            </summary>
            <ul className="course-list compact">
              {list.map((c) => (
                <li key={c.course_code}>
                  <span className="mono">{c.course_code}</span> {c.text}{" "}
                  {reason === "skipped" ? (
                    <button
                      type="button"
                      className="ghost small"
                      onClick={() => onUnset(c.course_code)}
                    >
                      Bỏ chọn chưa học
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="secondary small"
                      onClick={() => onInclude(c.course_code)}
                    >
                      Học kỳ này
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </details>
        ))}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Chưa học được hoặc đã xong</h2>
          <p>{data.not_eligible.length} học phần</p>
        </div>
        <ul className="course-list compact">
          {data.not_eligible.map((c) => (
            <li key={c.course_code}>
              <span className="mono">{c.course_code}</span>{" "}
              {c.text ?? c.course_name}
              {c.missing_prerequisites &&
                c.missing_prerequisites.length > 0 && (
                  <span className="hint">
                    {" "}
                    · còn thiếu{" "}
                    <Prerequisites groups={c.missing_prerequisites} />
                  </span>
                )}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
