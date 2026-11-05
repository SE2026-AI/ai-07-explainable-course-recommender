import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

/**
 * Kế hoạch học kỳ đang soạn của một sinh viên: danh sách mã học phần, theo thứ tự người dùng thêm.
 * Chỉ là bản nháp phía client, lưu tạm trong trình duyệt; kiểm tra hợp lệ là việc của plan-check.
 */
interface PlanState {
  codes: string[];
  add(code: string): void;
  remove(code: string): void;
  clear(): void;
}

const PlanContext = createContext<PlanState | null>(null);

function load(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((c): c is string => typeof c === "string") : [];
  } catch {
    return [];
  }
}

export function PlanProvider({ storageKey, children }: { storageKey: string; children: ReactNode }) {
  const [codes, setCodes] = useState<string[]>(() => load(storageKey));
  useEffect(() => setCodes(load(storageKey)), [storageKey]);
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(codes));
    } catch {
      // Không lưu được thì kế hoạch chỉ sống trong phiên này.
    }
  }, [storageKey, codes]);
  const value = useMemo<PlanState>(
    () => ({
      codes,
      add: (code) => setCodes((cur) => (cur.includes(code) ? cur : [...cur, code])),
      remove: (code) => setCodes((cur) => cur.filter((c) => c !== code)),
      clear: () => setCodes([]),
    }),
    [codes],
  );
  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

export function usePlan(): PlanState {
  const plan = useContext(PlanContext);
  if (!plan) throw new Error("usePlan phải nằm trong PlanProvider");
  return plan;
}
