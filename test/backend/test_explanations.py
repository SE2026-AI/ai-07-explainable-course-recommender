"""T-07 Explanations: every reason is grounded in score components or catalog/profile evidence (Q-09)."""

from backend.application import recommend as uc
from backend.domain import explanations as ex
from conftest import make_profile


def test_every_reason_has_resolvable_evidence(demo):
    profile = make_profile("BASE", interest_ids=("DATA",))
    resp = uc.recommend(demo, profile, None, request_id="t")
    for item in resp["eligible"] + resp["ineligible"]:
        assert item["reasons"], item["course_id"]
        for reason in item["reasons"]:
            assert reason["code"] in ex.REASON_CODES
            assert reason["evidence_refs"]
        assert set(item["reason_codes"]) <= ex.REASON_CODES


def test_blocked_course_lists_exact_missing_prerequisite(demo):
    resp = uc.recommend(demo, make_profile("BASE"), None, request_id="t")
    ai = next(i for i in resp["ineligible"] if i["course_id"] == "AI301")
    assert ai["direct_missing_prerequisite_ids"] == ["ST201"]
    assert "ST201" in ai["reasons"][0]["text"]


def test_goal_reason_cites_contribution(demo):
    resp = uc.recommend(demo, make_profile("BASE"), {"goal_match": 0.8, "workload_fit": 0.2}, request_id="t")
    st = next(i for i in resp["eligible"] if i["course_id"] == "ST201")
    goal = next(r for r in st["reasons"] if r["code"] == "GOAL_MATCH")
    assert goal["component"] == "goal_match"
    assert {"source": "catalog-demo-v1", "record_id": "goal:ML_ENGINEER"} in goal["evidence_refs"]


def test_unresolvable_evidence_is_dropped(demo):
    profile = make_profile("BASE")
    fake = ex.Reason(ex.GOAL_MATCH, "made up", (("catalog-demo-v1", "NOPE999"),))
    unknown_code = ex.Reason("BECAUSE_I_SAID_SO", "x", (("catalog-demo-v1", "ST201"),))
    good = ex.Reason(ex.WORKLOAD_FIT, "ok", (("catalog-demo-v1", "ST201"), ("profile", "workload_preference")))
    kept, dropped = ex.verify_evidence([fake, unknown_code, good], demo, profile)
    assert kept == [good] and dropped == [ex.GOAL_MATCH, "BECAUSE_I_SAID_SO"]


def test_why_not_eligible_but_lower_rank(demo):
    resp = uc.why_not(demo, make_profile("BASE"), ["SE201", "CS101"], {"goal_match": 0.8, "workload_fit": 0.2}, request_id="t")
    se, cs = resp["results"]
    assert se["eligible"] and se["rank"] == 2 and se["reason_codes"][0] == ex.LOWER_RANK
    assert not cs["eligible"] and cs["reason_codes"] == ["COMPLETED"]
