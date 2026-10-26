import { ApiError, userMessageFor } from "../api/errors";

export function ErrorBanner({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const routing = error instanceof ApiError && error.isRoutingError;
  return (
    <div className={`banner ${routing ? "error" : "warn"}`} role="alert">
      <div>
        <p>{userMessageFor(error)}</p>
        {error instanceof ApiError && (
          <p className="hint mono">
            {error.status > 0 && `HTTP ${error.status} · `}
            {error.code}
            {error.userMessage !== error.message && ` · ${error.message}`}
          </p>
        )}
      </div>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          Thử lại
        </button>
      )}
    </div>
  );
}
