"""Shared fixtures: demo catalog and the BASE/FAILED/READY profiles from the reference fixture."""

import json
from pathlib import Path

import pytest

from backend.data import CatalogRepository
from backend.domain.profile import HistoryRecord, StudentProfile, WorkloadPreference

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "docs/architecture/contracts/examples"
REFERENCE = json.loads((ROOT / "docs/tasks/prompts/fixtures/reference-scenarios.json").read_text(encoding="utf-8"))


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8-sig"))


def make_profile(name: str = "BASE", **overrides) -> StudentProfile:
    ref = REFERENCE["profiles"][name]
    history = tuple(HistoryRecord(c, "passed", float(g), "Y1S1") for c, g in ref.get("passed", {}).items())
    history += tuple(HistoryRecord(c, "failed", float(g), "Y1S1") for c, g in ref.get("failed", {}).items())
    goal = ref.get("career_goal")
    base = dict(
        profile_id=f"SYN-{name}", history=history, career_goal_ids=(goal,) if goal else (), interest_ids=(),
        workload_preference=WorkloadPreference(12, "lower"), max_credits_per_term=ref["max_credits"], excluded_course_ids=(),
    )
    base.update(overrides)
    return StudentProfile(**base)


@pytest.fixture(scope="session")
def repo() -> CatalogRepository:
    return CatalogRepository.from_directory()


@pytest.fixture(scope="session")
def demo(repo):
    return repo.get("catalog-demo-v1")


@pytest.fixture(scope="session")
def synthetic(repo):
    return repo.get("catalog-synthetic-v1")
