import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { AccountClient, Session } from "../api/v2/types";

interface AccountState {
  api: AccountClient;
  session: Session | null;
  loading: boolean;
  error: unknown;
  refresh(): Promise<void>;
  clear(): void;
}
const AccountContext = createContext<AccountState | null>(null);
export function AccountProvider({ api, children }: { api: AccountClient; children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const refresh = useCallback(async () => {
    setError(null);
    try { setSession(await api.me()); }
    catch (e) {
      setSession(null);
      if (!(e instanceof ApiError && e.code === "unauthenticated")) setError(e);
    } finally { setLoading(false); }
  }, [api]);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    const unsubscribe = api.onUnauthenticated(() => { if (active) { setSession(null); setError(null); } });
    api.me(controller.signal).then((value) => { if (active) { setSession(value); setError(null); } }).catch((e) => {
      if (active && !controller.signal.aborted) {
        setSession(null);
        if (!(e instanceof ApiError && e.code === "unauthenticated")) setError(e);
      }
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); unsubscribe(); };
  }, [api]);
  return <AccountContext.Provider value={{ api, session, loading, error, refresh, clear: () => setSession(null) }}>{children}</AccountContext.Provider>;
}
export function useAccount() {
  const state = useContext(AccountContext);
  if (!state) throw new Error("AccountProvider is missing");
  return state;
}
export function safeReturnTo(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || /[\s\\]/.test(value) || /^\/dang-(nhap|ky)(?:[/?#]|$)/.test(value)) return "/cua-toi";
  return value;
}
export function RequireAccount({ children }: { children: ReactNode }) {
  const account = useAccount();
  const location = useLocation();
  if (account.loading) return <p role="status">Đang kiểm tra phiên đăng nhập…</p>;
  if (account.error) return <section className="panel"><p role="alert">Chưa kết nối được tài khoản.</p><button onClick={() => void account.refresh()}>Thử lại kết nối</button></section>;
  if (!account.session) return <Navigate to={`/dang-nhap?next=${encodeURIComponent(location.pathname + location.search + location.hash)}`} replace />;
  return children;
}
export function AccountNav() {
  const { session, loading, api, clear } = useAccount();
  const [error, setError] = useState(false);
  const navigate = useNavigate();
  if (loading) return <span className="muted">Tài khoản…</span>;
  if (!session) return <Link to="/dang-nhap">Đăng nhập</Link>;
  async function logout() {
    setError(false);
    try { await api.logout(); clear(); navigate("/dang-nhap", { replace: true }); }
    catch { setError(true); }
  }
  return <>
    <Link to="/cua-toi">Bảng điểm của tôi</Link>
    <Link to="/tai-khoan" title={session.user.email}>Tài khoản</Link>
    <button className="ghost" onClick={() => void logout()}>Đăng xuất</button>
    {error && <span role="alert">Chưa đăng xuất được. Hãy thử lại.</span>}
  </>;
}
