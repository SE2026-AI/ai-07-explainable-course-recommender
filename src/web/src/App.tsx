import { useEffect, useState } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import { ApiError, createApiClient, type ApiClient } from "./api/client";
import {
  CONTRACT_VERSION,
  type CatalogCourse,
  type Graph,
  type Profile,
  type RecommendationResponse,
} from "./api/types";
import profileFixture from "./api/mocks/profile.mock.json";
import meta from "./api/mocks/meta.mock.json";
import { DEFAULT_WEIGHTS, loadDraft, saveDraft, sameJson } from "./lib/profile";
import { explainView, resultsView } from "./lib/presentation";
import { ProfilePage } from "./pages/ProfilePage";
import { ResultsPage } from "./pages/ResultsPage";
import { CourseDetail } from "./pages/CourseDetail";
import { WhyNot } from "./components/ExplanationPanel/WhyNot";
const defaultClient = createApiClient();
export default function App({
  client = defaultClient,
}: {
  client?: ApiClient;
}) {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile>(
    () => loadDraft()?.profile ?? (profileFixture.profile as Profile),
  );
  const [courses, setCourses] = useState<CatalogCourse[]>([]);
  const [graph, setGraph] = useState<Graph | null>(null);
  const [version, setVersion] = useState(profileFixture.catalog_version);
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [submitted, setSubmitted] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(false);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [error, setError] = useState("");
  const [catalogError, setCatalogError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setCatalogLoading(true);
      setCatalogError("");
      try {
        let page = await client.courses(undefined, controller.signal);
        const items = [...page.items];
        const cursors = new Set<string>();
        while (page.next_cursor) {
          if (cursors.has(page.next_cursor))
            throw new Error("Cursor catalog bị lặp.");
          cursors.add(page.next_cursor);
          page = await client.courses(
            page.catalog_version,
            controller.signal,
            page.next_cursor,
          );
          items.push(...page.items);
        }
        const links = await client.graph(
          page.catalog_version,
          controller.signal,
        );
        if (!controller.signal.aborted) {
          setCourses(items);
          setVersion(page.catalog_version);
          setGraph(links);
        }
      } catch (err) {
        if (!controller.signal.aborted)
          setCatalogError(
            err instanceof Error ? err.message : "Không tải được catalog.",
          );
      } finally {
        if (!controller.signal.aborted) setCatalogLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [client, retry]);
  useEffect(() => {
    saveDraft({ catalogVersion: version, profile, weights: DEFAULT_WEIGHTS });
  }, [version, profile]);
  async function recommend() {
    setLoading(true);
    setError("");
    setFieldErrors({});
    try {
      const response = await client.recommend({
        contract_version: CONTRACT_VERSION,
        catalog_version: version,
        request_id: crypto.randomUUID(),
        profile,
        weights: DEFAULT_WEIGHTS,
        include_ineligible: true,
      });
      setData(response);
      setSubmitted(structuredClone(profile));
      navigate("/results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được gợi ý.");
      if (err instanceof ApiError) setFieldErrors(err.fieldErrors);
    } finally {
      setLoading(false);
    }
  }
  async function ask(id: string) {
    const response = await client.whyNot({
      contract_version: CONTRACT_VERSION,
      catalog_version: version,
      request_id: crypto.randomUUID(),
      profile,
      course_ids: [id],
      weights: DEFAULT_WEIGHTS,
    });
    const row = response.results.find((r) => r.course_id === id);
    if (!row)
      throw new Error("Chưa có giải thích cho môn này trong dữ liệu trả về.");
    return explainView(row);
  }
  const stale = submitted !== null && !sameJson(submitted, profile);
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Gợi ý môn học có giải thích</h1>
        <nav aria-label="Điều hướng chính">
          <NavLink to="/profile">Hồ sơ</NavLink>
          <NavLink to="/results">Kết quả</NavLink>
          <NavLink
            to={
              courses[0] ? `/course/${courses[0].course_id}` : "/course/AI301"
            }
          >
            Chi tiết môn
          </NavLink>
          <NavLink to="/explain">Giải thích</NavLink>
        </nav>
      </header>
      <main className="route-content">
        {client.mode === "mock" && (
          <p className="banner info">
            Chế độ mock: phát lại fixture cố định, không tính lại theo hồ sơ.
            Panel có mẫu giải thích cho AI301.
          </p>
        )}
        {catalogLoading && <p role="status">Đang tải danh mục…</p>}
        {catalogError && (
          <div className="banner warn" role="alert">
            {catalogError}
            <button onClick={() => setRetry((n) => n + 1)}>Thử lại</button>
          </div>
        )}
        {error && (
          <div className="banner warn" role="alert">
            {error}
          </div>
        )}
        {stale && (
          <p role="status" className="banner info">
            Hồ sơ đã thay đổi. Bấm Gợi ý môn học để cập nhật kết quả.
          </p>
        )}
        <Routes>
          <Route path="/" element={<Navigate to="/profile" replace />} />
          <Route
            path="/profile"
            element={
              <ProfilePage
                profile={profile}
                meta={meta}
                courses={courses}
                fieldErrors={fieldErrors}
                onChange={setProfile}
                footer={
                  <button
                    className="primary"
                    disabled={loading || catalogLoading || !!catalogError}
                    onClick={() => void recommend()}
                  >
                    {loading ? "Đang tải gợi ý…" : "Gợi ý môn học"}
                  </button>
                }
              />
            }
          />
          <Route
            path="/results"
            element={
              data ? (
                <>
                  <button
                    disabled={loading || !!catalogError}
                    onClick={() => void recommend()}
                  >
                    {loading ? "Đang tải…" : "Cập nhật gợi ý"}
                  </button>
                  {data.warnings?.map((w, i) => (
                    <p role="status" key={i}>
                      {w.code}: {w.message}
                    </p>
                  ))}
                  {data.status === "degraded" && (
                    <p role="status">Kết quả không đầy đủ.</p>
                  )}
                  <ResultsPage
                    data={resultsView(data, courses)}
                    stale={stale}
                  />
                </>
              ) : (
                <section className="panel">
                  <h2>Chưa có kết quả</h2>
                  <p>Nhập hồ sơ và gửi yêu cầu gợi ý.</p>
                  <Link to="/profile">Mở hồ sơ</Link>
                </section>
              )
            }
          />
          <Route
            path="/course/:id"
            element={
              catalogLoading ? (
                <p role="status">Đang tải chi tiết…</p>
              ) : (
                <CourseDetail courses={courses} graph={graph} onAsk={ask} />
              )
            }
          />
          <Route
            path="/explain"
            element={
              <WhyNot
                key={JSON.stringify(profile)}
                courses={courses}
                disabled={catalogLoading || !!catalogError}
                onAsk={ask}
              />
            }
          />
          <Route
            path="*"
            element={
              <section className="panel">
                <h2>Không tìm thấy trang</h2>
                <Link to="/profile">Về hồ sơ</Link>
              </section>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
