import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import type { ApiClient } from "../api/client";
import { ApiError } from "../api/errors";
import type { Profile, ProfileIn, SavedTranscript } from "../api/v2/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { ProgressBar } from "../components/ProgressBar";
import { safeReturnTo, useAccount } from "../lib/account";
import { fromBody, incompleteRows, toBody } from "../lib/transcriptDraft";
import { useApi } from "../lib/useApi";
import { TranscriptEntry } from "./TranscriptEntryPage";

function FieldError({ error, field }: { error: unknown; field: string }) {
  const message = error instanceof ApiError ? error.fieldErrors[field] : undefined;
  return message ? <small role="alert" className="field-error">{message}</small> : null;
}

export function LoginPage({ register = false }: { register?: boolean }) {
  const { api, session, refresh } = useAccount();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const next = safeReturnTo(params.get("next"));
  if (session) return <Navigate to={next} replace />;
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null); setBusy(true);
    try {
      await api[register ? "register" : "login"]({ email, password });
      setPassword(""); await refresh(); navigate(next, { replace: true });
    } catch (e) { setError(e); }
    finally { setBusy(false); }
  }
  return <section className="panel account-form">
    <p className="eyebrow">Hồ sơ học tập cá nhân</p>
    <h2>{register ? "Tạo tài khoản" : "Đăng nhập"}</h2>
    <p>Lưu bảng điểm theo tài khoản để tiếp tục học tập ở lần đăng nhập sau.</p>
    <form onSubmit={(e) => void submit(e)}>
      <label>Email<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <FieldError error={error} field="email" />
      <label>Mật khẩu<input type="password" autoComplete={register ? "new-password" : "current-password"} minLength={8} maxLength={128} required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      <FieldError error={error} field="password" />
      {error !== null && <ErrorBanner error={error} />}
      {error instanceof ApiError && error.code === "too_many_attempts" && typeof error.details.retry_after_seconds === "number" && <p>Thử lại sau khoảng {error.details.retry_after_seconds} giây.</p>}
      <button className="primary" disabled={busy}>{busy ? "Đang xử lý…" : register ? "Đăng ký" : "Đăng nhập"}</button>
    </form>
    <p><Link to={`${register ? "/dang-nhap" : "/dang-ky"}?next=${encodeURIComponent(next)}`}>{register ? "Đã có tài khoản? Đăng nhập" : "Chưa có tài khoản? Đăng ký"}</Link></p>
    {!register && <p className="muted">Quên mật khẩu? Liên hệ quản trị viên để đặt lại. Bản này chưa gửi email xác minh.</p>}
  </section>;
}

export function AccountPage({ client }: { client: ApiClient }) {
  const { api, session, refresh, clear } = useAccount();
  const profile = session!.profile;
  const [catalog, retry] = useApi((signal) => client.curricula("HUS", signal), [client]);
  const [curriculum, setCurriculum] = useState(profile?.curriculum_code ?? "");
  const [cohort, setCohort] = useState(profile?.cohort_year?.toString() ?? "");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState<ProfileIn | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const navigate = useNavigate();
  async function operation(action: () => Promise<void>) {
    setBusy(true); setError(null); setMessage("");
    try { await action(); } catch (e) { setError(e); } finally { setBusy(false); }
  }
  async function choose(event: FormEvent) {
    event.preventDefault();
    const body: ProfileIn = { curriculum_code: curriculum, ...(cohort ? { cohort_year: Number(cohort) } : {}) };
    await operation(async () => {
      try { await api.profile(body); await refresh(); setMessage("Đã lưu khung chương trình."); }
      catch (e) { if (e instanceof ApiError && e.code === "transcript_not_empty") setPending(body); throw e; }
    });
  }
  return <div className="account-page">
    <section className="panel">
      <h2>Tài khoản của tôi</h2><p>{session!.user.email}</p>
      <p>Bảng điểm và kế hoạch thuộc tài khoản của bạn. Danh mục công khai vẫn đọc từ API v1.</p>
      <div className="row"><Link className="button-link" to="/cua-toi">Bảng điểm của tôi</Link><Link className="button-link" to="/cua-toi/tien-trinh">Tiến trình học tập</Link></div>
    </section>
    <section className="panel account-form">
      <h3>Khung chương trình của tôi</h3>
      {catalog.state === "error" && <ErrorBanner error={catalog.error} onRetry={retry} />}
      <form onSubmit={(e) => void choose(e)}>
        <label>Chương trình đào tạo<select required disabled={catalog.state !== "ok"} value={curriculum} onChange={(e) => setCurriculum(e.target.value)}>
          <option value="">Chọn khung của HUS</option>
          {catalog.state === "ok" && catalog.data.filter((c) => c.university_code === "HUS" && c.status === "active").map((c) => <option key={c.curriculum_code} value={c.curriculum_code}>{c.name} · {c.curriculum_code}</option>)}
        </select></label>
        <FieldError error={error} field="curriculum_code" />
        <label>Khóa nhập học (không bắt buộc)<input type="number" min={2000} max={2100} step={1} value={cohort} onChange={(e) => setCohort(e.target.value)} /></label>
        <FieldError error={error} field="cohort_year" />
        <button className="primary" disabled={busy || catalog.state !== "ok"}>Lưu khung chương trình</button>
      </form>
      {pending && <div role="alertdialog" aria-label="Đổi khung và xóa bảng điểm">
        <h4>Bảng điểm còn kết quả của khung cũ</h4>
        <p>Hãy xuất file JSON dự phòng ở Bảng điểm của tôi trước. Xác nhận sẽ xóa toàn bộ bảng điểm rồi đổi sang khung mới.</p>
        <button disabled={busy} onClick={() => void operation(async () => {
          await api.saveTranscript({ semesters_completed: profile?.semesters_completed ?? 0, results: [] });
          await api.profile(pending); setPending(null); await refresh(); setMessage("Đã xóa bảng điểm và đổi khung.");
        })}>Xóa bảng điểm và đổi khung</button>
        <button className="ghost" disabled={busy} onClick={() => setPending(null)}>Giữ khung hiện tại</button>
      </div>}
    </section>
    <section className="panel account-form">
      <h3>Đổi mật khẩu</h3>
      <form onSubmit={(e) => { e.preventDefault(); void operation(async () => {
        await api.password({ current_password: currentPassword, new_password: newPassword });
        setCurrentPassword(""); setNewPassword(""); setMessage("Đã đổi mật khẩu. Các phiên khác đã được đăng xuất.");
      }); }}>
        <label>Mật khẩu hiện tại<input type="password" autoComplete="current-password" required maxLength={128} value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} /></label>
        <FieldError error={error} field="current_password" />
        <label>Mật khẩu mới<input type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /></label>
        <FieldError error={error} field="new_password" />
        <button disabled={busy}>Đổi mật khẩu</button>
      </form>
    </section>
    <section className="panel account-form danger-zone">
      <h3>Xóa tài khoản</h3><p>Xóa vĩnh viễn tài khoản cùng bảng điểm, kế hoạch và lịch sử. Hãy xuất dữ liệu cần giữ trước.</p>
      {!deleteOpen ? <button className="secondary" onClick={() => setDeleteOpen(true)}>Tôi muốn xóa tài khoản</button> :
        <form aria-label="Xác nhận xóa tài khoản" onSubmit={(e) => { e.preventDefault(); void operation(async () => {
          await api.deleteAccount({ password: deletePassword }); setDeletePassword(""); clear(); navigate("/dang-nhap", { replace: true });
        }); }}>
          <label>Nhập mật khẩu để xác nhận xóa<input type="password" autoComplete="current-password" required maxLength={128} value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} /></label>
          <button disabled={busy}>Xóa vĩnh viễn tài khoản</button><button type="button" className="ghost" disabled={busy} onClick={() => { setDeleteOpen(false); setDeletePassword(""); }}>Hủy xóa</button>
        </form>}
    </section>
    {error !== null && <ErrorBanner error={error} />}
    {message && <p role="status" className="banner info">{message}</p>}
  </div>;
}

export function MyTranscriptPage({ client }: { client: ApiClient }) {
  const { session } = useAccount();
  if (!session!.profile) return <Navigate to="/tai-khoan" replace />;
  return <SavedTranscript key={session!.user.user_id + session!.profile.curriculum_code} client={client} profile={session!.profile} />;
}

function SavedTranscript({ client, profile }: { client: ApiClient; profile: Profile }) {
  const { api, refresh } = useAccount();
  const [stored, retry] = useApi((signal) => api.transcript(signal), [api, profile.curriculum_code]);
  if (stored.state === "error") return <ErrorBanner error={stored.error} onRetry={retry} />;
  if (stored.state !== "ok") return <p role="status">Đang tải bảng điểm đã lưu…</p>;
  return <SavedEditor key={profile.curriculum_code} client={client} stored={stored.data} refresh={refresh} />;
}
function SavedEditor({ client, stored, refresh }: { client: ApiClient; stored: SavedTranscript; refresh(): Promise<void> }) {
  const { api } = useAccount();
  const [semesters, setSemesters] = useState(stored.semesters_completed);
  const [initial, setInitial] = useState(stored);
  const [revision, setRevision] = useState(0);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [legacy, setLegacy] = useState(() => {
    if (stored.updated_at || stored.results.length) return null;
    try {
      const raw = localStorage.getItem(`ai07.transcript.HUS.${stored.curriculum_code}`);
      const parsed = raw ? fromBody(JSON.parse(raw)) : null;
      return parsed && Object.keys(parsed.draft).length ? parsed : null;
    } catch { return null; }
  });
  useEffect(() => { setNotice(""); }, [semesters]);
  return <>
    <section className="panel">
      <h2>Bảng điểm lưu theo tài khoản</h2>
      <label>Số kỳ đã hoàn thành<input aria-label="Số kỳ đã hoàn thành trên tài khoản" type="number" min={0} max={12} step={1} value={semesters} onChange={(e) => {
        const value = Number(e.target.value); if (Number.isInteger(value) && value >= 0 && value <= 12) setSemesters(value);
      }} /></label>
      <p>Chỉ lưu lên tài khoản khi bấm Lưu bảng điểm. Bạn vẫn có thể nhập và xuất file JSON.</p>
      <Link to="/cua-toi/tien-trinh">Xem tiến trình và điều kiện tốt nghiệp</Link>
    </section>
    {legacy && <section className="panel" role="region" aria-label="Bản nháp trên trình duyệt">
      <h3>Đưa bản nháp trên trình duyệt lên tài khoản?</h3>
      <p>Phát hiện {Object.keys(legacy.draft).length} môn của cùng khung. Bảng điểm chưa được gửi đi. Chỉ tiếp tục nếu đây là dữ liệu của bạn.</p>
      <button disabled={busy} onClick={() => {
        if (!Number.isInteger(legacy.semesters) || legacy.semesters < 0 || legacy.semesters > 12 || incompleteRows(legacy.draft).length) {
          setError(new Error("Bản nháp chưa đủ điểm hoặc số kỳ chưa hợp lệ. Hãy hoàn thiện trong chế độ tự nhập trước.")); return;
        }
        setBusy(true); setError(null);
        const body = toBody(legacy.draft, [], legacy.semesters).body;
        api.saveTranscript(body).then(async (saved) => {
          setInitial(saved); setSemesters(saved.semesters_completed); setRevision((n) => n + 1);
          try { localStorage.removeItem(`ai07.transcript.HUS.${stored.curriculum_code}`); } catch { /* Browser storage may be unavailable. */ }
          setLegacy(null); setNotice("Đã đưa bản nháp lên tài khoản."); await refresh();
        }).catch(setError).finally(() => setBusy(false));
      }}>Đưa bản nháp lên tài khoản</button>
      <button className="ghost" disabled={busy} onClick={() => setLegacy(null)}>Không đưa lên tài khoản</button>
    </section>}
    {notice && <p role="status" className="banner info">{notice}</p>}
    {error !== null && <ErrorBanner error={error} />}
    <TranscriptEntry key={revision} client={client} uni="HUS" curriculum={stored.curriculum_code} semesters={semesters} persistence={{
      initial,
      onSemestersChange: setSemesters,
      save: async (body) => {
        await api.saveTranscript(body); setNotice("Đã lưu bảng điểm trên tài khoản."); await refresh();
        return api.progress();
      },
    }} />
  </>;
}

export function MyProgressPage() {
  const { api, session } = useAccount();
  const [result, retry] = useApi((signal) => api.progress(signal), [api]);
  if (!session!.profile) return <Navigate to="/tai-khoan" replace />;
  if (result.state === "error") return <ErrorBanner error={result.error} onRetry={retry} />;
  if (result.state !== "ok") return <p role="status">Đang tải tiến trình…</p>;
  const data = result.data;
  return <section className="panel">
    <h2>Tiến trình học tập của tôi</h2><p className="mono">{data.curriculum_code}</p>
    <div className="account-metrics"><p><strong>{data.credits_earned} / {data.total_credits}</strong> tín chỉ tốt nghiệp</p><p>GPA <strong>{data.gpa == null ? "Chưa có điểm" : data.gpa.toLocaleString("vi-VN")}</strong></p></div>
    <ProgressBar value={data.credits_earned} max={data.total_credits} label="Tín chỉ tốt nghiệp đã hoàn thành" />
    <h3>Tiến độ từng khối</h3>
    <ul>{(data.blocks ?? []).map((block) => <li key={block.block_code}>{block.block_code}: {block.earned_credits} / {block.required_credits} tín chỉ{!block.counts_toward_total && " (điều kiện riêng, không cộng vào tổng)"}</li>)}</ul>
    <h3>Điều kiện tốt nghiệp ngoài tổng tín chỉ</h3>
    <p>Kỹ năng bổ trợ là điều kiện tốt nghiệp riêng, không cộng vào tổng {data.total_credits} tín chỉ.</p>
    <ul>{data.graduation_conditions.map((condition) => <li key={condition.block_code}><strong>{condition.met ? "Đã hoàn thành" : "Chưa hoàn thành"} · {condition.block_name}</strong><p>{condition.text}</p>{condition.missing_courses.length > 0 && <p>Còn thiếu: {condition.missing_courses.join(", ")}</p>}</li>)}</ul>
    <Link className="button-link" to="/cua-toi">Sửa bảng điểm</Link>
  </section>;
}
