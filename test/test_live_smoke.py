"""Regression checks for restored PR #57 smoke script; no PostgreSQL required."""
import importlib.util
from pathlib import Path


def script():
    spec = importlib.util.spec_from_file_location("live_smoke", Path(__file__).parents[1]/"scripts/smoke_transcripts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_four_fixtures_call_both_endpoints(monkeypatch):
    module = script()
    calls = []
    def post(url, body):
        calls.append((url, body))
        return (200, {"items": []}) if url.endswith("/recommendations") else (200, {"credits_earned": 0})
    monkeypatch.setattr(module, "post", post)
    monkeypatch.setattr("sys.argv", ["smoke_transcripts.py"])
    assert module.main() == 0
    assert len(calls) == 8
    assert all("results" in body for _, body in calls)


def test_missing_recommendations_is_failure_now_api5_is_on_main(monkeypatch):
    module = script()
    monkeypatch.setattr(module, "post", lambda url, body: (404, None) if url.endswith("/recommendations") else (200, {}))
    monkeypatch.setattr("sys.argv", ["smoke_transcripts.py"])
    assert module.main() == 1


def test_network_or_invalid_json_response_is_failure(monkeypatch):
    module = script()
    monkeypatch.setattr(module, "post", lambda url, body: (0, None))
    monkeypatch.setattr("sys.argv", ["smoke_transcripts.py"])
    assert module.main() == 1


def test_no_fixtures_is_not_silent_success(monkeypatch, tmp_path):
    module = script()
    monkeypatch.setattr(module, "FIXTURES", tmp_path)
    monkeypatch.setattr("sys.argv", ["smoke_transcripts.py"])
    assert module.main() == 1
