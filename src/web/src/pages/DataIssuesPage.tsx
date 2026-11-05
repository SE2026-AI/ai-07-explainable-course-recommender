import type { ApiClient } from "../api/client";
import { ErrorBanner } from "../components/ErrorBanner";
import { useApi } from "../lib/useApi";

const STATUS_LABEL: Record<string, string> = {
  open: "Đang mở",
  resolved_in_data: "Đã xử lý trong dữ liệu",
  closed: "Đã đóng",
};

/** Các chỗ văn bản CTĐT gốc mâu thuẫn hoặc thiếu (§6.8). */
export function DataIssuesPage({ client }: { client: ApiClient }) {
  const [issues, retry] = useApi((s) => client.dataIssues(s), [client]);
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Vấn đề dữ liệu</h2>
        <p>Những chỗ văn bản gốc mâu thuẫn hoặc thiếu, được ghi lại thay vì tự suy đoán.</p>
      </div>
      {issues.state === "loading" && <p role="status">Đang tải…</p>}
      {issues.state === "error" && <ErrorBanner error={issues.error} onRetry={retry} />}
      {issues.state === "ok" &&
        ((issues.data.issues ?? []).length === 0 ? (
          <p className="muted">Không có vấn đề dữ liệu nào.</p>
        ) : (
          <ul className="issues">
            {(issues.data.issues ?? []).map((i) => (
              <li key={`${i.source_code}/${i.entity_type}/${i.entity_key}/${i.issue_type}`}>
                <p>{i.description}</p>
                <p className="hint">
                  {i.source_title} ({i.document_number}) · {STATUS_LABEL[i.status] ?? i.status}
                </p>
              </li>
            ))}
          </ul>
        ))}
    </section>
  );
}
