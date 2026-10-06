import { useState, type FormEvent } from "react";
import type { PresetName, Role, Session } from "../lib/session";
import { AlertIcon, ArrowIcon, CapIcon, CheckIcon, EyeIcon, UserIcon } from "./Icons";

interface Props {
  onEnter(session: Session): void;
}

const PRESET_NOTE: Record<PresetName, string> = {
  BASE: "Đã qua CS101, MA101",
  FAILED: "Trượt MA101",
  READY: "Đã qua cả ST201",
};

/** DEMO login: no credential is checked or sent anywhere. It only picks a synthetic profile. */
export function Login({ onEnter }: Props) {
  const [role, setRole] = useState<Role>("student");
  const [account, setAccount] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [preset, setPreset] = useState<PresetName>("BASE");
  const [tried, setTried] = useState(false);

  const accountMissing = tried && !account.trim();
  const passwordMissing = tried && !password;

  function submit(e: FormEvent) {
    e.preventDefault();
    setTried(true);
    if (!account.trim() || !password) return;
    onEnter({ displayName: account.trim(), role, preset });
  }

  return (
    <div className="login">
      <section className="login-hero" aria-label="Giới thiệu">
        <div className="brand">
          <div className="logo light"><CapIcon /></div>
          <span className="brand-name">AI-07 · Gợi ý môn học có giải thích</span>
        </div>
        <div className="hero-body">
          <h1>Biết nên học môn gì — và vì sao.</h1>
          <p>Gợi ý dựa trên lịch sử học, mục tiêu nghề nghiệp và quỹ thời gian của bạn. Mỗi điểm số đều tách được thành từng lý do.</p>
          <div className="hero-card" aria-hidden="true">
            <div className="hero-card-head">
              <span className="rank small">1</span>
              <div><strong>Xác suất thống kê</strong><div className="mono muted">ST201</div></div>
              <span className="hero-score">77.8%</span>
            </div>
            <div className="stack thin">
              <span style={{ width: "55.6%", background: "var(--c-goal)" }} />
              <span style={{ width: "11.1%", background: "var(--c-interest)" }} />
              <span style={{ width: "11.1%", background: "var(--c-workload)" }} />
            </div>
            <div className="muted">Phù hợp mục tiêu ML Engineer · mở khóa AI301</div>
          </div>
        </div>
        <ul className="hero-points">
          <li><CheckIcon />Giải thích từng điểm số</li>
          <li><CheckIcon />Kế hoạch kỳ &amp; lộ trình</li>
          <li><CheckIcon />Đồ thị môn tiên quyết</li>
        </ul>
      </section>

      <section className="login-panel" aria-labelledby="login-title">
        <form className="login-form" onSubmit={submit} noValidate>
          <div>
            <h2 id="login-title">Đăng nhập</h2>
            <p className="muted">Bản demo: không kiểm tra mật khẩu, chỉ dùng hồ sơ giả lập.</p>
          </div>

          <fieldset className="segmented wide" aria-label="Vai trò">
            <label><input type="radio" name="role" checked={role === "student"} onChange={() => setRole("student")} /><span>Sinh viên</span></label>
            <label><input type="radio" name="role" checked={role === "advisor"} onChange={() => setRole("advisor")} /><span>Cố vấn học tập</span></label>
          </fieldset>

          {(accountMissing || passwordMissing) && (
            <div className="banner error" role="alert">
              <AlertIcon />
              <span>{accountMissing && passwordMissing ? "Nhập tài khoản và mật khẩu để tiếp tục." : accountMissing ? "Chưa nhập tài khoản." : "Chưa nhập mật khẩu."}</span>
            </div>
          )}

          <label className="field">
            {role === "student" ? "MSSV hoặc email trường" : "Email cán bộ"}
            <input type="text" autoComplete="username" value={account} aria-invalid={accountMissing}
              placeholder={role === "student" ? "VD: 22001535" : "ten@truong.edu.vn"} onChange={(e) => setAccount(e.target.value)} />
          </label>

          <div className="field">
            <label htmlFor="login-password">Mật khẩu</label>
            <div className="pw">
              <input id="login-password" type={showPw ? "text" : "password"} autoComplete="current-password" value={password}
                aria-invalid={passwordMissing} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" className="icon ghost" aria-label={showPw ? "Ẩn mật khẩu" : "Hiện mật khẩu"} aria-pressed={showPw} onClick={() => setShowPw(!showPw)}>
                <EyeIcon />
              </button>
            </div>
          </div>

          <div>
            <div className="field-title" id="preset-title">Hồ sơ demo</div>
            <div className="chip-grid" role="group" aria-labelledby="preset-title">
              {(Object.keys(PRESET_NOTE) as PresetName[]).map((p) => (
                <button key={p} type="button" className="chip stacked" aria-pressed={preset === p} onClick={() => setPreset(p)}>
                  {p}<small>{PRESET_NOTE[p]}</small>
                </button>
              ))}
            </div>
          </div>

          <button type="submit" className="primary big">Đăng nhập <ArrowIcon /></button>

          <div className="or"><span />hoặc<span /></div>

          <button type="button" className="secondary big" onClick={() => onEnter({ displayName: "Khách", role: "student", preset })}>
            <UserIcon /> Dùng thử với hồ sơ demo
          </button>
          <p className="hint center">Không nhập thông tin sinh viên thật — dữ liệu chỉ lưu trên trình duyệt này.</p>
        </form>
      </section>
    </div>
  );
}
