import { useEffect, useState } from "react";

export type Load<T> =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "ok"; data: T }
  | { state: "error"; error: unknown };

/** Gọi `fetcher` mỗi khi `deps` đổi; hủy request cũ bằng AbortController. `null` nghĩa là chưa gọi. */
export function useApi<T>(
  fetcher: ((signal: AbortSignal) => Promise<T>) | null,
  deps: readonly unknown[],
): [Load<T>, () => void] {
  const [load, setLoad] = useState<Load<T>>({ state: "idle" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!fetcher) {
      setLoad({ state: "idle" });
      return;
    }
    const controller = new AbortController();
    setLoad({ state: "loading" });
    fetcher(controller.signal).then(
      (data) => !controller.signal.aborted && setLoad({ state: "ok", data }),
      (error) => !controller.signal.aborted && setLoad({ state: "error", error }),
    );
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);
  return [load, () => setAttempt((n) => n + 1)];
}
