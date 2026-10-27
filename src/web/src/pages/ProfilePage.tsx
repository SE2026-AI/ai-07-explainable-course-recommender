import type { ReactNode } from "react";
import type {
  CatalogCourse,
  CatalogMeta,
  Direction,
  HistoryState,
  Profile,
} from "../api/types";
import { PRESETS, sameJson } from "../lib/profile";
import { CloseIcon } from "../components/Icons";

interface Props {
  profile: Profile;
  meta: CatalogMeta | null;
  courses: CatalogCourse[];
  fieldErrors: Record<string, string>;
  onChange(profile: Profile): void;
  /** Submit controls rendered at the bottom of the panel. */
  footer?: ReactNode;
}

const STATE_LABEL: Record<HistoryState, string> = {
  passed: "Đã qua",
  failed: "Chưa đạt",
  planned: "Dự định",
};

export function ProfilePage({
  profile,
  meta,
  courses,
  fieldErrors,
  onChange,
  footer,
}: Props) {
  const set = (patch: Partial<Profile>) => onChange({ ...profile, ...patch });
  const setRow = (i: number, patch: Partial<Profile["history"][number]>) =>
    set({
      history: profile.history.map((h, j) =>
        j === i ? { ...h, ...patch } : h,
      ),
    });
  const toggle = (list: string[], id: string) =>
    list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
  const err = (field: string) => fieldErrors[field];
  const used = new Set(profile.history.map((h) => h.course_id));
  const nextCourse = courses.find((c) => !used.has(c.course_id))?.course_id;
  const presetNames = Object.keys(PRESETS) as (keyof typeof PRESETS)[];

  return (
    <section className="panel" aria-labelledby="profile-title">
      <div className="panel-head">
        <h2 id="profile-title">Hồ sơ sinh viên</h2>
        <span className="eyebrow">Bước 1 · giả lập</span>
      </div>

      <div>
        <div className="field-title" id="presets-title">
          Hồ sơ mẫu
        </div>
        <div className="chip-grid" role="group" aria-labelledby="presets-title">
          {presetNames.map((name) => (
            <button
              key={name}
              type="button"
              className="chip"
              aria-pressed={sameJson(profile, PRESETS[name])}
              onClick={() => onChange(structuredClone(PRESETS[name]))}
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      <fieldset>
        <legend>Lịch sử học</legend>
        <div className="history">
          {profile.history.length === 0 && (
            <p className="muted history-empty">Chưa có môn nào.</p>
          )}
          {profile.history.map((h, i) => {
            const gradeErr = err(`profile.history.${i}.grade`);
            const rowErr =
              err(`profile.history.${i}.course_id`) ??
              err(`profile.history.${i}`);
            return (
              <div className="history-row" key={i}>
                <label>
                  <span className="sr-only">Môn {i + 1}</span>
                  <select
                    value={h.course_id}
                    onChange={(e) => setRow(i, { course_id: e.target.value })}
                  >
                    {courses.map((c) => (
                      <option
                        key={c.course_id}
                        value={c.course_id}
                        disabled={
                          c.course_id !== h.course_id && used.has(c.course_id)
                        }
                      >
                        {c.course_id} · {c.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="sr-only">Trạng thái {h.course_id}</span>
                  <select
                    value={h.state}
                    onChange={(e) =>
                      setRow(i, { state: e.target.value as HistoryState })
                    }
                  >
                    {(Object.keys(STATE_LABEL) as HistoryState[]).map((s) => (
                      <option key={s} value={s}>
                        {STATE_LABEL[s]}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="sr-only">Điểm {h.course_id}</span>
                  <input
                    type="number"
                    step="0.1"
                    inputMode="decimal"
                    placeholder="Điểm"
                    value={h.grade ?? ""}
                    aria-invalid={!!gradeErr}
                    aria-describedby={gradeErr ? `grade-err-${i}` : undefined}
                    onChange={(e) =>
                      setRow(i, {
                        grade:
                          e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </label>
                <button
                  type="button"
                  className="icon"
                  aria-label={`Xóa ${h.course_id}`}
                  onClick={() =>
                    set({ history: profile.history.filter((_, j) => j !== i) })
                  }
                >
                  <CloseIcon />
                </button>
                {gradeErr && (
                  <p className="field-error" id={`grade-err-${i}`} role="alert">
                    Điểm {h.course_id}: {gradeErr}
                  </p>
                )}
                {rowErr && (
                  <p className="field-error" role="alert">
                    {rowErr}
                  </p>
                )}
              </div>
            );
          })}
        </div>
        <button
          type="button"
          className="dashed"
          disabled={!nextCourse}
          onClick={() =>
            nextCourse &&
            set({
              history: [
                ...profile.history,
                { course_id: nextCourse, state: "passed", grade: 7 },
              ],
            })
          }
        >
          + Thêm môn đã học
        </button>
        <p className="hint">
          Thang điểm 0–10 · qua môn khi điểm ≥ 5 (quy định giả lập của dự án).
        </p>
      </fieldset>

      <fieldset>
        <legend>Mục tiêu nghề nghiệp</legend>
        <div className="pills">
          {meta?.goals.map((g) => (
            <label key={g.goal_id} className="pill">
              <input
                type="checkbox"
                checked={profile.career_goal_ids.includes(g.goal_id)}
                onChange={() =>
                  set({
                    career_goal_ids: toggle(profile.career_goal_ids, g.goal_id),
                  })
                }
              />
              <span>{g.title}</span>
            </label>
          ))}
        </div>
        {err("profile.career_goal_ids.0") && (
          <p className="field-error" role="alert">
            {err("profile.career_goal_ids.0")}
          </p>
        )}
      </fieldset>

      <fieldset>
        <legend>Sở thích</legend>
        <div className="pills">
          {meta?.topics.map((t) => (
            <label key={t} className="pill">
              <input
                type="checkbox"
                checked={profile.interest_ids.includes(t)}
                onChange={() =>
                  set({ interest_ids: toggle(profile.interest_ids, t) })
                }
              />
              <span>{t}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend>Khối lượng học</legend>
        <div className="grid-2">
          <label>
            Giờ/tuần
            <input
              type="number"
              min={1}
              max={168}
              value={profile.workload_preference.hours_per_week_budget}
              aria-invalid={
                !!err("profile.workload_preference.hours_per_week_budget")
              }
              onChange={(e) =>
                set({
                  workload_preference: {
                    ...profile.workload_preference,
                    hours_per_week_budget: Number(e.target.value),
                  },
                })
              }
            />
          </label>
          <label>
            Tín chỉ tối đa / kỳ
            <input
              type="number"
              min={1}
              max={60}
              value={profile.max_credits_per_term}
              aria-invalid={!!err("profile.max_credits_per_term")}
              onChange={(e) =>
                set({ max_credits_per_term: Number(e.target.value) })
              }
            />
          </label>
        </div>
        <label>
          Ưu tiên
          <select
            value={profile.workload_preference.direction}
            onChange={(e) =>
              set({
                workload_preference: {
                  ...profile.workload_preference,
                  direction: e.target.value as Direction,
                },
              })
            }
          >
            <option value="lower">Nhẹ hơn</option>
            <option value="neutral">Vừa ngân sách</option>
            <option value="higher">Nặng hơn</option>
          </select>
        </label>
        {err("profile.workload_preference.hours_per_week_budget") && (
          <p className="field-error" role="alert">
            Ngân sách:{" "}
            {err("profile.workload_preference.hours_per_week_budget")}
          </p>
        )}
        {err("profile.max_credits_per_term") && (
          <p className="field-error" role="alert">
            Tín chỉ: {err("profile.max_credits_per_term")}
          </p>
        )}
      </fieldset>

      {footer && <div className="submit-area">{footer}</div>}
    </section>
  );
}
