import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, createLiveClient, createMockClient, type ApiClient, type ApiMode } from "./api/client";
import type { CatalogCourse, CatalogMeta, Profile, RecommendationResponse, SimulationResponse, Weights } from "./api/types";
import { COMPONENTS } from "./api/types";
import { ProfileForm } from "./components/ProfileForm";
import { AlertIcon, CapIcon } from "./components/Icons";
import { Results, type RankPreview } from "./components/Results";
import { WhatIf } from "./components/WhatIf";
import { WhyNot } from "./components/WhyNot";
import { createLatestRunner } from "./lib/latest";
import { DEFAULT_WEIGHTS, PRESETS, loadDraft, sameJson, saveDraft } from "./lib/profile";

type Fault = "" | "ranking_failure" | "explanation_failure" | "catalog_unavailable";

interface Submitted {
  data: RecommendationResponse;
  profile: Profile;
  weights: Weights;
  catalogVersion: string;
}

interface Props {
  /** Injected in tests; by default the mode toggle builds a live or mock client. */
  clientFor?: (mode: ApiMode, fault: Fault) => ApiClient;
  initialMode?: ApiMode;
  simulateDebounceMs?: number;
}

const defaultClientFor = (mode: ApiMode, fault: Fault) => (mode === "mock" ? createMockClient() : createLiveClient("/v1", fault || undefined));

/** Normalize "profile.history[0].grade" (domain) and "profile.history.0.grade" (schema) to the same key. */
function fieldErrorsOf(err: unknown): Record<string, string> {
  if (!(err instanceof ApiError) || err.status !== 422) return {};
  return Object.fromEntries(Object.entries(err.fieldErrors).map(([k, v]) => [k.replace(/\[(\d+)\]/g, ".$1"), v]));
}

function describe(err: unknown): string {
  if (!(err instanceof ApiError)) return "Lỗi không xác định.";
  if (err.status === 0) return "Không kết nối được tới API. Kiểm tra backend đang chạy (uvicorn) hoặc chuyển sang chế độ MOCK.";
  if (err.status === 503) return `API tạm thời không khả dụng (${err.code}). Có thể thử lại.`;
  if (err.status === 409) return `Phiên bản catalog không còn hợp lệ (${err.code}). Hãy tải lại trang.`;
  if (err.status === 422) return `Dữ liệu chưa hợp lệ (${err.code}): ${err.message}`;
  return `${err.code}: ${err.message}`;
}

export default function App({ clientFor = defaultClientFor, initialMode = "live", simulateDebounceMs = 250 }: Props) {
  const saved = useMemo(loadDraft, []);
  const [mode, setMode] = useState<ApiMode>(initialMode);
  const [fault, setFault] = useState<Fault>("");
  const client = useMemo(() => clientFor(mode, fault), [clientFor, mode, fault]);

  const [meta, setMeta] = useState<CatalogMeta | null>(null);
  const [courses, setCourses] = useState<CatalogCourse[]>([]);
  const [catalogVersion, setCatalogVersion] = useState(saved?.catalogVersion ?? "catalog-demo-v1");
  const [profile, setProfile] = useState<Profile>(saved?.profile ?? structuredClone(PRESETS.BASE));
  const [weights, setWeights] = useState<Weights>(saved?.weights ?? DEFAULT_WEIGHTS);

  const [submitted, setSubmitted] = useState<Submitted | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);

  const recRunner = useRef(createLatestRunner()).current;
  const simRunner = useRef(createLatestRunner()).current;
  const metaRunner = useRef(createLatestRunner()).current;

  useEffect(() => saveDraft({ catalogVersion, profile, weights }), [catalogVersion, profile, weights]);

  // Catalog metadata for the form; reloaded when the mode or catalog changes.
  useEffect(() => {
    metaRunner.run(async (signal) => Promise.all([client.meta(catalogVersion, signal), client.courses(catalogVersion, signal)]))
      .then((r) => {
        if (r.stale) return;
        setMeta(r.value[0]);
        setCourses(r.value[1].items);
        if (r.value[0].catalog_version !== catalogVersion) setCatalogVersion(r.value[0].catalog_version);
      })
      .catch((err) => setError(err));
    return () => metaRunner.cancel();
  }, [client, catalogVersion, metaRunner]);

  const recommend = useCallback(async (useWeights: Weights) => {
    setLoading(true);
    setError(null);
    simRunner.cancel();
    const snapshot = { profile: structuredClone(profile), weights: { ...useWeights }, catalogVersion };
    try {
      const r = await recRunner.run((signal) => client.recommend(snapshot.catalogVersion, snapshot.profile, snapshot.weights, signal));
      if (r.stale) return;
      setSubmitted({ data: r.value, ...snapshot });
      setWeights(snapshot.weights);
      setSimulation(null);
      setSimError(null);
    } catch (err) {
      setError(err); // draft (profile/weights) is deliberately left untouched
    } finally {
      setLoading(false);
    }
  }, [client, profile, catalogVersion, recRunner, simRunner]);

  // What-if: when sliders differ from the submitted baseline, ask the backend for a comparison (latest wins).
  const scenarioChanged = submitted != null && !sameJson(weights, submitted.weights);
  const weightTotal = COMPONENTS.reduce((s, c) => s + weights[c], 0);
  useEffect(() => {
    if (!submitted || !scenarioChanged || weightTotal <= 0) {
      simRunner.cancel();
      setSimLoading(false);
      return;
    }
    setSimLoading(true);
    const timer = setTimeout(() => {
      simRunner.run((signal) => client.simulate(submitted.catalogVersion, submitted.profile, submitted.weights, weights, `ui-${Date.now()}`, signal))
        .then((r) => {
          if (r.stale) return;
          setSimulation(r.value);
          setSimError(null);
          setSimLoading(false);
        })
        .catch((err) => {
          setSimError(describe(err));
          setSimLoading(false);
        });
    }, simulateDebounceMs);
    return () => clearTimeout(timer);
  }, [client, submitted, weights, scenarioChanged, weightTotal, simRunner, simulateDebounceMs]);

  async function askWhyNot(courseId: string) {
    try {
      const resp = await client.whyNot(catalogVersion, profile, [courseId], weights);
      return resp.results[0] ?? null;
    } catch (err) {
      setError(err);
      return null;
    }
  }

  const stale = submitted != null && (!sameJson(profile, submitted.profile) || catalogVersion !== submitted.catalogVersion);
  const fieldErrors = fieldErrorsOf(error);
  const data = submitted?.data;

  const preview: RankPreview | undefined = scenarioChanged && simulation
    ? Object.fromEntries(simulation.changes.map((c) => [c.course_id, { rank: c.rank_after, score: c.score_after }]))
    : undefined;

  return (
    <div className="app">
      <header className="top">
        <div className="top-inner">
          <div className="brand">
            <div className="logo"><CapIcon /></div>
            <div>
              <h1>Gợi ý môn học có giải thích</h1>
              <p>AI-07 · dữ liệu giả lập · điểm là mức phù hợp theo quy tắc, không phải xác suất thành công</p>
            </div>
          </div>
          <div className="top-tools">
            {mode === "mock" && <span className="badge mock" data-testid="mock-badge">MOCK · dữ liệu ghi sẵn cho hồ sơ BASE, không tính toán</span>}
            <fieldset className="segmented" aria-label="Nguồn dữ liệu">
              <label>
                <input type="radio" name="mode" checked={mode === "live"} onChange={() => { setMode("live"); setSubmitted(null); }} />
                <span>API thật</span>
              </label>
              <label>
                <input type="radio" name="mode" checked={mode === "mock"} onChange={() => { setMode("mock"); setFault(""); setSubmitted(null); }} />
                <span>Mock</span>
              </label>
            </fieldset>
          </div>
        </div>
      </header>

      <main className="layout">
        <div className="side">
          <ProfileForm
            profile={profile} meta={meta} courses={courses} fieldErrors={fieldErrors} onChange={setProfile}
            footer={(
              <>
                <button type="button" className="primary" onClick={() => recommend(weights)} disabled={loading || weightTotal <= 0}>
                  {loading ? "Đang gợi ý…" : "Gợi ý môn học"}
                </button>
                {mode === "live" && (
                  <label className="fault">
                    Giả lập lỗi (kiểm thử)
                    <select value={fault} onChange={(e) => setFault(e.target.value as Fault)}>
                      <option value="">không</option>
                      <option value="ranking_failure">ranking lỗi (degraded)</option>
                      <option value="explanation_failure">giải thích lỗi (degraded)</option>
                      <option value="catalog_unavailable">catalog mất (503)</option>
                    </select>
                  </label>
                )}
              </>
            )}
          />
        </div>

        <div className="main">
          <div aria-live="polite" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {error != null && (
              <div className="banner error" role="alert" data-testid="error-banner">
                <AlertIcon />
                <span>{describe(error)} <span className="muted">Hồ sơ nháp của bạn vẫn được giữ.</span></span>
              </div>
            )}
            {stale && data && (
              <div className="banner info" data-testid="stale-banner">
                <AlertIcon />
                <span>Hồ sơ đã thay đổi; kết quả dưới đây là của hồ sơ trước. Bấm “Gợi ý môn học” để cập nhật.</span>
              </div>
            )}
            {preview && !stale && (
              <div className="banner info" role="status">
                <AlertIcon />
                <span>Đang xem kịch bản what-if — thứ hạng gốc vẫn được giữ đến khi bạn bấm “Dùng làm gốc”.</span>
              </div>
            )}
            {data?.status === "degraded" && (
              <div className="banner warn" data-testid="degraded-banner">
                <AlertIcon />
                <div>
                  Kết quả không đầy đủ (degraded):
                  <ul>{data.warnings.map((w, i) => <li key={i}>{w.code}: {w.message}</li>)}</ul>
                </div>
              </div>
            )}
            {data && data.status !== "degraded" && data.warnings.length > 0 && (
              <div className="banner info">
                <ul>{data.warnings.map((w, i) => <li key={i}>{w.message}</li>)}</ul>
              </div>
            )}
          </div>
          {loading && !data && <p className="muted" role="status">Đang tải gợi ý…</p>}
          {!data && !loading && error == null && (
            <section className="panel empty-state">
              <div>
                <div className="eyebrow">Bước 2 · kết quả</div>
                <h2>Môn nên học kỳ tới</h2>
              </div>
              <p>Chọn hồ sơ mẫu (BASE, FAILED, READY) hoặc tự nhập, rồi bấm “Gợi ý môn học”.</p>
            </section>
          )}
          {data && <Results data={data} stale={stale} preview={preview} />}
        </div>

        <div className="side">
          <WhatIf
            weights={weights}
            baseline={submitted?.weights ?? null}
            onChange={setWeights}
            onAdopt={() => recommend(weights)}
            onReset={() => submitted && setWeights(submitted.weights)}
            simulation={scenarioChanged ? simulation : null}
            loading={simLoading}
            error={simError}
          />
          <WhyNot courses={courses} disabled={courses.length === 0} onAsk={askWhyNot} />
        </div>
      </main>
    </div>
  );
}
