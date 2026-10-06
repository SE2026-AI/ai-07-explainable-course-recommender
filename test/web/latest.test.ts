// AC-4: a slow older response can never overwrite the newest one.
import { describe, expect, it } from "vitest";
import { createLatestRunner } from "@web/lib/latest";

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

describe("createLatestRunner", () => {
  it("drops an older response that resolves after a newer one", async () => {
    const runner = createLatestRunner();
    const older = deferred<string>();
    const newer = deferred<string>();
    const first = runner.run(() => older.promise);
    const second = runner.run(() => newer.promise);
    newer.resolve("new");
    older.resolve("old");
    expect(await second).toEqual({ stale: false, value: "new" });
    expect(await first).toEqual({ stale: true });
  });

  it("aborts the previous request signal", async () => {
    const runner = createLatestRunner();
    let firstSignal: AbortSignal | undefined;
    const first = runner.run((signal) => {
      firstSignal = signal;
      return new Promise<string>(() => {});
    });
    void first;
    await runner.run(async () => "x");
    expect(firstSignal?.aborted).toBe(true);
  });

  it("propagates real errors of the latest run", async () => {
    const runner = createLatestRunner();
    await expect(runner.run(async () => { throw new Error("boom"); })).rejects.toThrow("boom");
  });
});
