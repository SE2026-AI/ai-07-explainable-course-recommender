"""T-02: synthetic data generator is deterministic and respects the proposed academic policy."""

import importlib.util
import json
import random
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gen", ROOT / "tools" / "generate_synthetic_data.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _generate(seed=42, count=300):
    catalog = gen.build_catalog()
    profiles, cohorts = gen.build_profiles(random.Random(seed), count, catalog["courses"])
    return catalog, profiles, cohorts


def test_same_seed_same_output():
    assert json.dumps(_generate(7)) == json.dumps(_generate(7))


def test_reference_courses_match_fixture():
    fixture = json.loads((ROOT / "docs/tasks/prompts/fixtures/reference-scenarios.json").read_text(encoding="utf-8"))
    courses = {c["course_id"]: c for c in gen.build_catalog()["courses"]}
    for ref in fixture["courses"]:
        course = courses[ref["course_id"]]
        assert course["credits"] == ref["credits"]
        assert course["mandatory_prerequisites"] == ref["prerequisites"]
        assert course["workload_hours_per_week"] == ref["workload"]


def test_catalog_rejects_cycles_and_dangling_refs():
    base = {"recommended_preparation": []}
    with pytest.raises(ValueError, match="cycle"):
        gen.validate_catalog([
            {**base, "course_id": "A", "mandatory_prerequisites": ["B"]},
            {**base, "course_id": "B", "mandatory_prerequisites": ["A"]},
        ])
    with pytest.raises(ValueError, match="unknown"):
        gen.validate_catalog([{**base, "course_id": "A", "mandatory_prerequisites": ["Z"]}])


def test_histories_respect_prerequisites_and_grades():
    catalog, profiles, _ = _generate()
    prereqs = {c["course_id"]: c["mandatory_prerequisites"] for c in catalog["courses"]}
    for profile in profiles:
        ids = [h["course_id"] for h in profile["history"]]
        assert len(ids) == len(set(ids)), profile["profile_id"]
        passed_at = {h["course_id"]: h["completed_term"] for h in profile["history"] if h["state"] == "passed"}
        for record in profile["history"]:
            assert (record["state"] == "passed") == (record["grade"] >= gen.PASSING_GRADE)
            for p in prereqs[record["course_id"]]:
                assert p in passed_at and passed_at[p] < record["completed_term"], (profile["profile_id"], record)


def test_cohort_labels_stay_out_of_profiles():
    _, profiles, cohorts = _generate()
    allowed = {"profile_id", "history", "career_goal_ids", "interest_ids",
               "workload_preference", "max_credits_per_term", "excluded_course_ids"}
    for profile in profiles:
        assert set(profile) <= allowed
        assert profile["profile_id"] in cohorts


def test_has_failed_cohort_always_has_a_failure():
    _, profiles, cohorts = _generate()
    for profile in profiles:
        if cohorts[profile["profile_id"]]["academic_pattern"] == "has_failed":
            assert any(h["state"] == "failed" for h in profile["history"]), profile["profile_id"]
