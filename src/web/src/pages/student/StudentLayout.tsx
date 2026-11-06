import { useEffect, useRef } from "react";
import { Link, NavLink, Outlet, useLocation, useOutletContext, useParams, useSearchParams } from "react-router-dom";
import type { ApiClient, StudentRef } from "../../api/client";
import { ApiError } from "../../api/errors";
import type { StudentProfile } from "../../api/schema";
import { ErrorBanner } from "../../components/ErrorBanner";
import { IconCalendar, IconGraph, IconList, IconSparkle, IconUser } from "../../components/Icons";
import { PlanProvider } from "../../lib/plan";
import { useApi } from "../../lib/useApi";

export interface StudentContext {
  client: ApiClient;
  ref: StudentRef;
  /** `term` của URL; vắng thì server dùng học kỳ mặc định (§3.1). */
  term?: string;
  profile: StudentProfile;
}

export function useStudent(): StudentContext {
  return useOutletContext<StudentContext>();
}

const TABS = [
  ["profile", "Hồ sơ", IconUser],
  ["status", "Trạng thái học phần", IconList],
  ["recommendations", "Gợi ý", IconSparkle],
  ["plan", "Kế hoạch học kỳ", IconCalendar],
  ["graph", "Sơ đồ tiên quyết", IconGraph],
] as const;

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts.at(-2)?.[0] ?? "") + (parts.at(-1)?.[0] ?? "")).toUpperCase();
}

/** Khung chung của các trang một sinh viên: tải hồ sơ một lần, chọn học kỳ, chuyển tab. */
export function StudentLayout({ client }: { client: ApiClient }) {
  const { uni = "", student = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const term = params.get("term") || undefined;
  const ref: StudentRef = { uni, student };

  const [profile, retry] = useApi((s) => client.profile(ref, { term }, s), [client, uni, student, term]);
  const [terms] = useApi((s) => client.terms(uni, s), [client, uni]);
  const search = term ? `?term=${encodeURIComponent(term)}` : "";
  const tabsRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  // Trên điện thoại thanh tab cuộn ngang: kéo tab đang mở vào khung nhìn.
  useEffect(() => {
    tabsRef.current?.querySelector<HTMLElement>("a.active")?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [pathname, profile.state]);

  if (profile.state === "loading" || profile.state === "idle")
    return (
      <div className="skeleton-head" role="status">
        <span className="sr-only">Đang tải hồ sơ…</span>
      </div>
    );
  if (profile.state === "error") {
    const notFound = profile.error instanceof ApiError && profile.error.code === "student_not_found";
    return (
      <section className="panel narrow">
        <ErrorBanner error={profile.error} onRetry={notFound ? undefined : retry} />
        <Link to="/students">Nhập mã sinh viên khác</Link>
      </section>
    );
  }

  const p = profile.data;
  return (
    <PlanProvider storageKey={`ai07.plan.${uni}.${student}`}>
      <section className="student-head">
        <div className="student-id">
          <span className="avatar" aria-hidden="true">
            {initials(p.full_name)}
          </span>
          <div>
            <h2>
              {p.full_name} <span className="mono muted">{p.student_code}</span>
            </h2>
            <ul className="meta-chips" aria-label="Thông tin chương trình">
              <li>{p.major_name}</li>
              <li className="mono">{p.curriculum_code}</li>
              <li>Khóa {p.cohort_year}</li>
            </ul>
          </div>
        </div>
        <label className="term-picker">
          Học kỳ đang xét
          <select
            value={term ?? p.term}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              next.set("term", e.target.value);
              setParams(next);
            }}
          >
            {terms.state === "ok" ? (
              terms.data.map((t) => (
                <option key={t.term_code} value={t.term_code}>
                  {t.name} ({t.term_code})
                </option>
              ))
            ) : (
              <option value={p.term}>{p.term}</option>
            )}
          </select>
        </label>
      </section>
      <nav className="tabs" aria-label="Trang của sinh viên" ref={tabsRef}>
        {TABS.map(([to, label, Icon]) => (
          <NavLink key={to} to={`${to}${search}`}>
            <Icon />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <Outlet context={{ client, ref, term, profile: p } satisfies StudentContext} />
    </PlanProvider>
  );
}
