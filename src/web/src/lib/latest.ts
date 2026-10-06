// "Latest request wins": each run aborts the previous one, and a response is delivered only if it belongs
// to the newest run. A slow older response can therefore never overwrite a newer scenario.

export interface LatestRunner {
  run<T>(task: (signal: AbortSignal) => Promise<T>): Promise<{ stale: true } | { stale: false; value: T }>;
  cancel(): void;
}

export function createLatestRunner(): LatestRunner {
  let current = 0;
  let controller: AbortController | null = null;
  return {
    async run(task) {
      controller?.abort();
      const id = ++current;
      const mine = new AbortController();
      controller = mine;
      try {
        const value = await task(mine.signal);
        return id === current ? { stale: false, value } : { stale: true };
      } catch (err) {
        if (id !== current || (err as Error).name === "AbortError") return { stale: true };
        throw err;
      }
    },
    cancel() {
      current++;
      controller?.abort();
      controller = null;
    },
  };
}
