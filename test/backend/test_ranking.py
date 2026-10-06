"""T-06 Ranking tests (required by the brief): arithmetic oracle, reconciliation, determinism, invalid weights."""

import math

import pytest

from backend.domain import ranking
from backend.domain.profile import satisfied_course_ids
from conftest import REFERENCE, make_profile

EX = REFERENCE["ranking_example"]


def _rank_oracle(weights):
    w = ranking.normalize_weights(weights)
    scored = [ranking.score(cid, comps, w) for cid, comps in EX["components"].items()]
    return {s.course_id: s for s in ranking.rank(scored)}


@pytest.mark.parametrize("weights_key, expected_key", [("career_weights", "career_expected_scores"),
                                                       ("light_weights", "light_expected_scores")])
def test_reference_arithmetic_oracle(weights_key, expected_key):
    result = _rank_oracle(EX[weights_key])
    for cid, expected in EX[expected_key].items():
        assert result[cid].total == pytest.approx(expected, abs=1e-9)


def test_order_reverses_between_settings():
    career, light = _rank_oracle(EX["career_weights"]), _rank_oracle(EX["light_weights"])
    assert (career["ST201"].rank, career["SE201"].rank) == (1, 2)
    assert (light["ST201"].rank, light["SE201"].rank) == (2, 1)


def test_contributions_reconcile_with_total(demo):
    profile = make_profile("BASE", interest_ids=("DATA",))
    satisfied = satisfied_course_ids(profile)
    for s in ranking.rank_courses(demo, profile, satisfied, ["ST201", "SE201"], ranking.normalize_weights(None)):
        assert abs(sum(c.contribution for c in s.components.values()) - s.total) <= 1e-9
        assert 0 <= s.total <= 1


def test_missing_components_renormalized():
    w = ranking.normalize_weights(None)  # .5/.2/.1/.2
    s = ranking.score("X", {"goal_match": 1.0, "interest_match": None, "preparation": None, "workload_fit": 0.5}, w)
    assert s.total == pytest.approx((0.5 * 1.0 + 0.2 * 0.5) / 0.7)
    assert s.missing_components == ["interest_match", "preparation"]
    assert s.components["goal_match"].effective_weight == pytest.approx(0.5 / 0.7)


def test_no_scorable_components_gives_no_score_not_zero():
    w = ranking.normalize_weights({"interest_match": 1})
    s = ranking.score("X", {"goal_match": 1.0, "interest_match": None, "preparation": None, "workload_fit": None}, w)
    assert s.total is None
    assert ranking.rank([s])[0].rank is None


def test_tie_break_by_course_id():
    w = ranking.normalize_weights({"goal_match": 1})
    tied = [ranking.score(cid, {"goal_match": 0.5}, w) for cid in ("SE201", "AA100", "ST201")]
    assert [s.course_id for s in ranking.rank(tied)] == ["AA100", "SE201", "ST201"]


def test_repeatable_output(demo):
    profile = make_profile("BASE", interest_ids=("DATA",))
    run = lambda: ranking.rank_courses(demo, profile, satisfied_course_ids(profile), ["SE201", "ST201"], ranking.normalize_weights(None))
    assert run() == run()


@pytest.mark.parametrize("weights", [
    {"goal_match": 0, "interest_match": 0, "preparation": 0, "workload_fit": 0},
    {"goal_match": -0.1, "workload_fit": 1},
    {"goal_match": math.nan},
    {"goal_match": math.inf},
    {"popularity": 1},
])
def test_invalid_weights_rejected(weights):
    with pytest.raises(ranking.InvalidWeights):
        ranking.normalize_weights(weights)


def test_weights_normalized_to_one():
    w = ranking.normalize_weights({"goal_match": 2, "workload_fit": 2})
    assert w == {"goal_match": 0.5, "interest_match": 0.0, "preparation": 0.0, "workload_fit": 0.5}


@pytest.mark.parametrize("hours, budget, direction, expected", [
    (6, 12, "lower", 0.5), (12, 12, "lower", 0.0), (18, 12, "lower", 0.0),
    (6, 12, "higher", 0.5), (18, 12, "higher", 1.0),
    (6, 12, "neutral", 1.0), (18, 12, "neutral", 0.5), (30, 12, "neutral", 0.0),
    (None, 12, "lower", None),
])
def test_workload_fit_formula(hours, budget, direction, expected):
    assert ranking.workload_fit(hours, budget, direction) == (pytest.approx(expected) if expected is not None else None)


def test_display_rounding_half_up():
    assert ranking.display_percent(0.8605) == 86.1
    assert ranking.display_percent(None) is None
