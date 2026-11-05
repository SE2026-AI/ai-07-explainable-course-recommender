import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { createApiClient, type ApiClient } from "./api/client";
import { ErrorBanner } from "./components/ErrorBanner";
import { useApi } from "./lib/useApi";
import { CatalogPage } from "./pages/CatalogPage";
import { DataIssuesPage } from "./pages/DataIssuesPage";
import { StudentPickerPage } from "./pages/StudentPickerPage";
import { CourseStatusPage } from "./pages/student/CourseStatusPage";
import { GraphPage } from "./pages/student/GraphPage";
import { PlanPage } from "./pages/student/PlanPage";
import { ProfilePage } from "./pages/student/ProfilePage";
import { RecommendationsPage } from "./pages/student/RecommendationsPage";
import { StudentLayout } from "./pages/student/StudentLayout";

const defaultClient = createApiClient();

export default function App({ client = defaultClient }: { client?: ApiClient }) {
  const [meta, retryMeta] = useApi((s) => client.meta(s), [client]);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Bỏ qua thanh điều hướng
      </a>
      <header className="top">
        <div className="top-inner">
          <Link to="/" className="brand" aria-label="Trang chủ: Gợi ý học phần có giải thích">
            <img src="/hus-logo.png" alt="Trường Đại học Khoa học Tự nhiên, ĐHQGHN" className="brand-logo" />
            <span className="brand-divider" aria-hidden="true" />
            <h1 className="brand-title">Gợi ý học phần có giải thích</h1>
          </Link>
          <nav aria-label="Điều hướng chính" className="top-tools">
            <NavLink to="/students">Sinh viên</NavLink>
            <NavLink to="/catalog">Khung chương trình</NavLink>
            <NavLink to="/data-issues">Vấn đề dữ liệu</NavLink>
            {client.mode === "mock" && <span className="badge mock">mock</span>}
          </nav>
        </div>
      </header>
      <main className="main app-main" id="main">
        {meta.state === "error" && <ErrorBanner error={meta.error} onRetry={retryMeta} />}
        {client.mode === "mock" && (
          <p className="banner info">
            Chế độ mock: phát lại nguyên văn ví dụ trong api-contract.md, không phụ thuộc mã sinh viên, học kỳ hay trọng
            số đã chọn.
          </p>
        )}
        <Routes>
          <Route path="/" element={<Navigate to="/students" replace />} />
          <Route path="/students" element={<StudentPickerPage client={client} />} />
          <Route path="/students/:uni/:student" element={<StudentLayout client={client} />}>
            <Route index element={<Navigate to="profile" replace />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="status" element={<CourseStatusPage />} />
            <Route path="recommendations" element={<RecommendationsPage />} />
            <Route path="plan" element={<PlanPage />} />
            <Route path="graph" element={<GraphPage />} />
          </Route>
          <Route path="/catalog" element={<CatalogPage client={client} />} />
          <Route path="/data-issues" element={<DataIssuesPage client={client} />} />
          <Route
            path="*"
            element={
              <section className="panel">
                <h2>Không tìm thấy trang</h2>
                <Link to="/students">Về trang chọn sinh viên</Link>
              </section>
            }
          />
        </Routes>
      </main>
      <footer className="foot">
        <div className="foot-inner">
          <span>AI-07 · Dữ liệu sinh viên là dữ liệu giả lập, không dùng cho đăng ký thật.</span>
          {/* §6.1: hiện algorithm_version để truy được nguyên nhân khi kết quả gợi ý thay đổi. */}
          {meta.state === "ok" && (
            <span className="mono" data-testid="meta">
              API {meta.data.api_version} · thuật toán {meta.data.algorithm} {meta.data.algorithm_version} · học kỳ mặc
              định {meta.data.default_term}
            </span>
          )}
        </div>
      </footer>
    </div>
  );
}
