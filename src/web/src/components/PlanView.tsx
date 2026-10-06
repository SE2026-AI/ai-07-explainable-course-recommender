import { useEffect, useMemo, useState } from "react";
import type { Profile, RecommendationResponse } from "../api/types";
import { sortTerms } from "../lib/roadmap";
import { AlertIcon, LockIcon, StarIcon } from "./Icons";

interface Props {
  data: RecommendationResponse | null;
  profile: Profile;
  terms: string[];
  loading: boolean;
  onRecommend(): void;
  onNavigate(view: "roadmap" | "graph"): void;
}

const TERM_LABEL: Record<string, string> = { SPRING: "Xuân", SUMMER: "Hè", FALL: "Thu" };
export const termLabel = (t: string) => {
  const [y, s] = t.split("-");
  return `${TERM_LABEL[s] ?? s} ${y}`;
};

const PLAN_KEY = "ai07.plans.v1";
function savePlan(profileId: string, term: string, ids: string[]): boolean {
  try {
    const all = JSON.parse(localStorage.getItem(PLAN_KEY) ?? "{}");
    all[`${profileId}:${term}`] = ids;
    localStorage.setItem(PLAN_KEY, JSON.stringify(all));
    return true;
  } catch {
    return false;
  }
}

export function NeedResults({ loading, onRecommend, title }: { loading: boolean; onRecommend(): void; title: string }) {
  return (
    <section className="panel empty-state">
      <h2>{title}</h2>
      <p>Màn này dùng kết quả gợi ý của hồ sơ hiện tại. Chưa có kết quả nào.</p>
      <button type="button" className="primary" onClick={onRecommend} disabled={loading}>{loading ? "Đang gợi ý…" : "Tạo gợi ý ngay"}</button>
    </section>
  );
}

export function PlanView({ data, profile, terms, loading, onRecommend, onNavigate }: Props) {
  const termList = useMemo(() => sortTerms(terms), [terms]);
  const [term, setTerm] = useState(termList[1] ?? termList[0] ?? "");
  const [selected, setSelected] = useState<string[]>([]);
  const [maxCredits, setMaxCredits] = useState(profile.max_credits_per_term);
  const [saved, setSaved] = useState<string | null>(null);
  const budget = profile.workload_preference.hours_per_week_budget;

  useEffect(() => { if (!term && termList.length) setTerm(termList[0]); }, [term, termList]);
  useEffect(() => setMaxCredits(profile.max_credits_per_term), [profile.max_credits_per_term]);
  useEffect(() => { setSelected([]); setSaved(null); }, [data]);

  if (!data) return <NeedResults loading={loading} onRecommend={onRecommend} title="Kế hoạch học kỳ" />;

  const cands = data.eligible.filter((c) => c.rank != null).sort((a, b) => a.rank! - b.rank!);
  const picked = cands.filter((c) => selected.includes(c.course_id));
  const credits = picked.reduce((s, c) => s + c.credits, 0);
  const hours = picked.reduce((s, c) => s + (c.workload_hours_per_week ?? 0), 0);
  const overCredits = credits > maxCredits;
  const overHours = hours > budget;
  const over = overCredits || overHours;
  const status = picked.length === 0 ? "empty" : over ? "infeasible" : "valid";

  const toggle = (id: string) => { setSaved(null); setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id])); };
  const autoPick = () => {
    let cr = 0, hr = 0;
    const ids: string[] = [];
    for (const c of cands) {
      const h = c.workload_hours_per_week ?? 0;
      if (cr + c.credits <= maxCredits && hr + h <= budget) { ids.push(c.course_id); cr += c.credits; hr += h; }
    }
    setSaved(null);
    setSelected(ids);
  };

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Chọn môn cho một học kỳ trong giới hạn tín chỉ và thời gian</div>
          <h1 className="page-title">Kế hoạch học kỳ</h1>
        </div>
        <fieldset className="segmented" aria-label="Học kỳ">
          {termList.map((t) => (
            <label key={t}><input type="radio" name="plan-term" checked={term === t} onChange={() => { setTerm(t); setSaved(null); }} /><span>{termLabel(t)}</span></label>
          ))}
        </fieldset>
      </div>

      <div className="split">
        <section className="split-main" aria-labelledby="cand-title">
          <div className="row-between">
            <h2 id="cand-title" className="h-small">Có thể học kỳ này <span className="count">· xếp theo mức phù hợp</span></h2>
            <button type="button" className="secondary accent" onClick={autoPick}><StarIcon /> Tự xếp theo hạng</button>
          </div>
          {cands.length === 0 && <p className="empty">Không có môn nào đủ điều kiện cho hồ sơ này.</p>}
          <ul className="cards">
            {cands.map((c) => {
              const on = selected.includes(c.course_id);
              return (
                <li key={c.course_id} className={`card plan-card${on ? " is-on" : ""}`} data-testid={`plan-${c.course_id}`}>
                  <span className="rank">{c.rank}</span>
                  <div className="card-title">
                    <div className="line"><span className="cid">{c.course_id}</span><h3>{c.title}</h3></div>
                    <p className="meta">{c.credits} tín chỉ{c.workload_hours_per_week != null && ` · ~${c.workload_hours_per_week} giờ/tuần`}{c.unlocks.length > 0 && ` · mở khóa ${c.unlocks.join(", ")}`}</p>
                  </div>
                  <div className="score-box">
                    <div className="score sm">{c.score_percent != null ? `${c.score_percent}%` : "—"}</div>
                    <div className="score-label">mức phù hợp</div>
                  </div>
                  <button type="button" className={on ? "primary toggle" : "secondary toggle"} aria-pressed={on} onClick={() => toggle(c.course_id)}>
                    {on ? "✓ Đã chọn" : "+ Thêm"}<span className="sr-only"> {c.course_id}</span>
                  </button>
                </li>
              );
            })}
          </ul>

          {data.ineligible.length > 0 && (
            <>
              <h2 className="h-small">Chưa học được kỳ này</h2>
              <ul className="mini-grid">
                {data.ineligible.map((c) => (
                  <li key={c.course_id} className="mini blocked">
                    <LockIcon />
                    <div>
                      <div><span className="cid">{c.course_id}</span> <strong>{c.title}</strong></div>
                      <div className="muted">
                        Cần qua {c.direct_missing_prerequisite_ids.join(", ") || "môn tiên quyết"} trước ·{" "}
                        <button type="button" className="link" onClick={() => onNavigate("roadmap")}>xem lộ trình</button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <aside className="panel split-side" aria-labelledby="sum-title">
          <div className="row-between">
            <h2 id="sum-title">{termLabel(term)} <span className="mono muted">{term}</span></h2>
            <span role="status" className={`status ${status}`}>{status === "empty" ? "Trống" : over ? "Không khả thi" : "Hợp lệ"}</span>
          </div>

          <div className="meter">
            <div className="row-between"><span>Tín chỉ</span><strong>{credits} / {maxCredits}</strong></div>
            <div className="bar-track" role="img" aria-label={`Đã dùng ${credits} trên ${maxCredits} tín chỉ`}>
              <span className={overCredits ? "over" : ""} style={{ width: `${Math.min(100, (credits / Math.max(1, maxCredits)) * 100)}%` }} />
            </div>
          </div>
          <div className="meter">
            <div className="row-between"><span>Thời gian / tuần</span><strong>{hours} / {budget} giờ</strong></div>
            <div className="bar-track" role="img" aria-label={`${hours} trên ${budget} giờ mỗi tuần`}>
              <span className={overHours ? "over" : "dark"} style={{ width: `${Math.min(100, (hours / Math.max(1, budget)) * 100)}%` }} />
            </div>
          </div>

          <div className="row-between">
            <span>Tín chỉ tối đa / kỳ</span>
            <div className="stepper">
              <button type="button" className="secondary" aria-label="Giảm tín chỉ tối đa" onClick={() => setMaxCredits((m) => Math.max(1, m - 1))}>−</button>
              <span>{maxCredits}</span>
              <button type="button" className="secondary" aria-label="Tăng tín chỉ tối đa" onClick={() => setMaxCredits((m) => Math.min(30, m + 1))}>+</button>
            </div>
          </div>

          <div className="picked">
            <div className="label-caps">Đã chọn</div>
            {picked.length === 0 && <p className="muted">Chưa chọn môn nào — bấm “Thêm” hoặc “Tự xếp theo hạng”.</p>}
            {picked.map((c) => (
              <div key={c.course_id} className="row-between picked-row"><span><span className="cid">{c.course_id}</span> {c.title}</span><span>{c.credits} TC</span></div>
            ))}
          </div>

          {over && (
            <div className="banner warn-orange" role="alert">
              <AlertIcon />
              <span>{overCredits ? `Vượt ${credits - maxCredits} tín chỉ so với giới hạn — bỏ bớt môn hoặc tăng giới hạn.` : `Vượt quỹ ${budget} giờ/tuần.`}</span>
            </div>
          )}
          {saved && <p className="muted" role="status">{saved}</p>}

          <button type="button" className="primary" disabled={status !== "valid"}
            onClick={() => setSaved(savePlan(profile.profile_id, term, selected) ? "Đã lưu kế hoạch trên trình duyệt này." : "Không lưu được (trình duyệt chặn bộ nhớ).")}>
            Lưu kế hoạch
          </button>
          <button type="button" className="link center" onClick={() => onNavigate("roadmap")}>Lên lộ trình nhiều kỳ →</button>
        </aside>
      </div>
    </main>
  );
}
