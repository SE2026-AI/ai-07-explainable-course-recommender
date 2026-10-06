import { useEffect, useMemo, useState } from "react";
import type { CatalogCourse, Profile, RecommendationResponse } from "../api/types";
import { passedIds, planRoadmap, sortTerms } from "../lib/roadmap";
import { AlertIcon, ArrowIcon, CheckIcon } from "./Icons";
import { termLabel } from "./PlanView";

interface Props {
  courses: CatalogCourse[];
  profile: Profile;
  terms: string[];
  data: RecommendationResponse | null;
  onNavigate(view: "plan" | "graph"): void;
}

export function RoadmapView({ courses, profile, terms, data, onNavigate }: Props) {
  const termList = useMemo(() => sortTerms(terms), [terms]);
  const done = useMemo(() => passedIds(profile.history), [profile.history]);
  const open = courses.filter((c) => !done.has(c.course_id));
  const defaultTargets = useMemo(() => {
    const blocked = data?.ineligible.map((c) => c.course_id) ?? [];
    return blocked.length ? blocked : open.slice(-2).map((c) => c.course_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, courses.length]);

  const [targets, setTargets] = useState<string[]>(defaultTargets);
  const [start, setStart] = useState(termList[1] ?? termList[0] ?? "");
  const [horizonCount, setHorizonCount] = useState(3);
  const [maxCredits, setMaxCredits] = useState(profile.max_credits_per_term);

  useEffect(() => setTargets(defaultTargets), [defaultTargets]);
  useEffect(() => { if (!start && termList.length) setStart(termList[0]); }, [start, termList]);
  useEffect(() => setMaxCredits(profile.max_credits_per_term), [profile.max_credits_per_term]);

  const horizon = termList.slice(Math.max(0, termList.indexOf(start)), Math.max(0, termList.indexOf(start)) + horizonCount);
  const result = useMemo(
    () => planRoadmap({ courses, history: profile.history, targets: targets.filter((t) => !done.has(t)), horizon, maxCreditsPerTerm: maxCredits }),
    [courses, profile.history, targets, done, horizon.join(","), maxCredits], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const byId = new Map(courses.map((c) => [c.course_id, c]));
  const termOf = new Map<string, number>();
  result.terms.forEach((t, i) => t.course_ids.forEach((id) => termOf.set(id, i)));

  const toggleTarget = (id: string) => setTargets((ts) => (ts.includes(id) ? ts.filter((x) => x !== id) : [...ts, id]));

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Xếp các môn mục tiêu qua nhiều học kỳ, tôn trọng thứ tự tiên quyết</div>
          <h1 className="page-title">Lộ trình nhiều kỳ</h1>
        </div>
        {targets.length > 0 && (
          <span role="status" className={`status ${result.status === "complete" ? "valid" : "infeasible"}`}>
            {result.status === "complete" ? "Xếp đủ mọi môn cần học" : `Còn ${result.unscheduled.length} môn chưa xếp được`}
          </span>
        )}
      </div>

      <section className="panel settings" aria-label="Thiết lập lộ trình">
        <fieldset>
          <legend>Môn mục tiêu</legend>
          <div className="pills">
            {open.map((c) => (
              <label key={c.course_id} className="pill mono-pill" title={c.title}>
                <input type="checkbox" checked={targets.includes(c.course_id)} onChange={() => toggleTarget(c.course_id)} />
                <span>{c.course_id}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="settings-row">
          <label>Bắt đầu
            <select value={start} onChange={(e) => setStart(e.target.value)}>
              {termList.map((t) => <option key={t} value={t}>{termLabel(t)} · {t}</option>)}
            </select>
          </label>
          <label>Số kỳ xét
            <select value={horizonCount} onChange={(e) => setHorizonCount(Number(e.target.value))}>
              {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n} kỳ</option>)}
            </select>
          </label>
          <label>Tín chỉ tối đa / kỳ
            <input type="number" min={1} max={30} value={maxCredits} onChange={(e) => setMaxCredits(Math.max(1, Number(e.target.value) || 1))} />
          </label>
          <div className="done-list">
            <span>Đã qua</span>
            <span className="mono ok-ink">{[...done].join(" · ") || "—"}</span>
          </div>
        </div>
      </section>

      {targets.length === 0 ? (
        <p className="empty">Chọn ít nhất một môn mục tiêu để xếp lộ trình.</p>
      ) : (
        <ol className="terms" aria-label="Các học kỳ">
          {result.terms.map((t, i) => (
            <li key={t.term_id} className="term" data-testid={`term-${t.term_id}`}>
              <div className="term-head">
                <span className={`term-no${t.course_ids.length ? "" : " idle"}`}>{i + 1}</span>
                <h2>{termLabel(t.term_id)}</h2>
                <span className="mono muted">{t.term_id}</span>
              </div>
              <div className="bar-track slim" role="img" aria-label={`${t.credits} trên ${maxCredits} tín chỉ`}>
                <span style={{ width: `${Math.min(100, (t.credits / maxCredits) * 100)}%` }} />
              </div>
              <div className="muted">{t.credits} / {maxCredits} tín chỉ{t.hours ? ` · ~${t.hours} giờ/tuần` : ""}</div>
              {t.course_ids.length === 0 && (
                <div className="term-empty">
                  <span>Còn trống — có thể thêm môn tự chọn.</span>
                  <button type="button" className="link" onClick={() => onNavigate("plan")}>Chọn môn cho kỳ</button>
                </div>
              )}
              {t.course_ids.map((id) => {
                const c = byId.get(id)!;
                const isTarget = targets.includes(id);
                const unlocks = courses.filter((d) => d.mandatory_prerequisites.includes(id) && termOf.has(d.course_id)).map((d) => d.course_id);
                const pre = c.mandatory_prerequisites;
                return (
                  <article key={id} className="card term-card">
                    <div className="card-title">
                      <div className="line"><span className="cid">{id}</span><h3>{c.title}</h3></div>
                      <p className="meta">{c.credits} tín chỉ · {isTarget ? "mục tiêu" : `cần cho ${result.requiredBy[id]?.join(", ")}`}</p>
                    </div>
                    <ul className="reasons">
                      <li>
                        <CheckIcon />
                        <span className="text">{pre.length === 0 ? "Không có môn tiên quyết" : `Đủ tiên quyết: ${pre.map((p) => (done.has(p) ? `${p} (đã qua)` : `${p} (kỳ ${termOf.get(p)! + 1})`)).join(", ")}`}</span>
                      </li>
                      {unlocks.length > 0 && <li className="next"><ArrowIcon /><span className="text">Mở khóa {unlocks.join(", ")} cho kỳ sau</span></li>}
                    </ul>
                  </article>
                );
              })}
            </li>
          ))}
        </ol>
      )}

      {result.unscheduled.length > 0 && (
        <div className="banner warn-orange" role="alert">
          <AlertIcon />
          <span>Chưa xếp được {result.unscheduled.join(", ")} trong {horizon.length} kỳ — thử tăng số kỳ hoặc tín chỉ tối đa.</span>
        </div>
      )}
      <p className="hint">
        Bản demo: lộ trình được xếp trên trình duyệt từ dữ liệu tiên quyết của catalog (chưa có API lộ trình).{" "}
        <button type="button" className="link" onClick={() => onNavigate("graph")}>Xem đồ thị tiên quyết</button>
      </p>
    </main>
  );
}
