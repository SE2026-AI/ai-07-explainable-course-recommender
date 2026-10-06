"""T-08 What-if: baseline is immutable, deltas only over comparable candidates (Q-04)."""

import copy

import pytest

from backend.application import recommend as uc
from backend.domain.simulation import InvalidScenario, Scenario
from conftest import make_profile

CAREER = {"goal_match": 0.8, "workload_fit": 0.2}
LIGHT = {"goal_match": 0.2, "workload_fit": 0.8}


def test_weight_change_keeps_baseline_and_reports_deltas(demo):
    profile = make_profile("BASE")
    weights = dict(CAREER)
    snapshot = (copy.deepcopy(profile), dict(weights))
    baseline_resp = uc.recommend(demo, profile, weights, request_id="b")
    resp = uc.simulate(demo, profile, weights, Scenario("whatif-light", "1", weights=LIGHT), baseline_version="base-v1", request_id="s")
    assert (profile, weights) == snapshot
    assert uc.recommend(demo, profile, weights, request_id="b") == baseline_resp
    assert resp["scenario_id"] == "whatif-light" and resp["baseline_version"] == "base-v1"
    assert resp["entered"] == [] and resp["exited"] == []
    assert {c["course_id"] for c in resp["changes"]} == {"ST201", "SE201"}
    assert resp["baseline"]["weights"]["goal_match"] == pytest.approx(0.8)
    assert resp["scenario"]["weights"]["goal_match"] == pytest.approx(0.2)


def test_hypothetical_pass_changes_eligibility_not_rank_delta(demo):
    resp = uc.simulate(demo, make_profile("BASE"), None, Scenario("hp", "1", hypothetical_passed=("ST201",)),
                       baseline_version="b", request_id="s")
    assert resp["entered"] == ["AI301"] and resp["exited"] == ["ST201"]
    assert [c["course_id"] for c in resp["changes"]] == ["SE201"]  # only shared candidates are compared


def test_same_scenario_is_repeatable(demo):
    run = lambda: uc.simulate(demo, make_profile("BASE"), CAREER, Scenario("s", "1", weights=LIGHT), baseline_version="b", request_id="s")
    assert run() == run()


@pytest.mark.parametrize("scenario, field", [
    (Scenario("x", "1", hypothetical_passed=("MISSING999",)), "scenario.hypothetical_passed"),
    (Scenario("x", "1", hypothetical_passed=("CS101",)), "scenario.hypothetical_passed"),
    (Scenario("x", "1", weights={"goal_match": 0}), "scenario.weights"),
    (Scenario("x", "1", career_goal_ids=("ASTRONAUT",)), "scenario.career_goal_ids[0]"),
])
def test_invalid_scenario_rejected(demo, scenario, field):
    profile = make_profile("BASE")
    before = copy.deepcopy(profile)
    with pytest.raises(InvalidScenario) as exc:
        uc.simulate(demo, profile, None, scenario, baseline_version="b", request_id="s")
    assert exc.value.field == field
    assert profile == before
