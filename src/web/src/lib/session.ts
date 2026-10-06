// Demo-only session: no authentication happens. It just remembers who entered and with which synthetic profile.
// Real auth/persistence is still an open question (docs/tasks/ARCHITECTURE_HANDOFF.md, item 5).

export type Role = "student" | "advisor";
export type PresetName = "BASE" | "FAILED" | "READY";

export interface Session {
  displayName: string;
  role: Role;
  preset: PresetName;
}

const KEY = "ai07.session.v1";

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function saveSession(session: Session | null): void {
  try {
    if (session) localStorage.setItem(KEY, JSON.stringify(session));
    else localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: the session lives only in memory */
  }
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "SV";
  const last = parts[parts.length - 1];
  return (parts.length > 1 ? parts[0][0] + last[0] : last.slice(0, 2)).toUpperCase();
}
