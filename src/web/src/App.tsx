import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { createApiClient, type ApiClient } from "./api/client";
import { ErrorBanner } from "./components/ErrorBanner";
import { useApi } from "./lib/useApi";
import { CatalogPage } from "./pages/CatalogPage";
import { DataIssuesPage } from "./pages/DataIssuesPage";

const defaultClient = createApiClient();

export default function App({ client = defaultClient }: { client?: ApiClient }) {
  const [meta, retryMeta] = useApi((s) => client.meta(s), [client]);
  return (
    <div className="app-shell">
      <header className="top">
        <div className="top-inner">
          <div className="brand">
            <h1>Gợi ý học phần có giải thích</h1>
            {/* §6.1: hiện algorithm_version để truy được nguyên nhân khi kết quả gợi ý thay đổi. */}
            {meta.state === "ok" && (
              <p className="hint" data-testid="meta">
                API {meta.data.api_version} · thuật toán {meta.data.algorithm} {meta.data.algorithm_version} ·
                học kỳ mặc định {meta.data.default_term}
              </p>
            )}
          </div>
          <nav aria-label="Điều hướng chính" className="top-tools">
            <NavLink to="/catalog">Khung chương trình</NavLink>
            <NavLink to="/data-issues">Vấn đề dữ liệu</NavLink>
            {client.mode === "mock" && <span className="badge mock">mock</span>}
          </nav>
        </div>
      </header>
      <main className="main">
        {meta.state === "error" && <ErrorBanner error={meta.error} onRetry={retryMeta} />}
        {client.mode === "mock" && (
          <p className="banner info">
            Chế độ mock: phát lại nguyên văn ví dụ trong api-contract.md, không phụ thuộc mã trường hay mã
            khung đã chọn.
          </p>
        )}
        <Routes>
          <Route path="/" element={<Navigate to="/catalog" replace />} />
          <Route path="/catalog" element={<CatalogPage client={client} />} />
          <Route path="/data-issues" element={<DataIssuesPage client={client} />} />
          <Route
            path="*"
            element={
              <section className="panel">
                <h2>Không tìm thấy trang</h2>
                <Link to="/catalog">Về khung chương trình</Link>
              </section>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
