"""T-04 Profile validation against the catalog and the adopted grade policy."""

import pytest

from backend.domain.profile import HistoryRecord, ProfileInvalid, check_profile, satisfied_course_ids, validate_profile
from conftest import make_profile


def codes(issues):
    return [i.code for i in issues]


def test_reference_profiles_are_valid(demo):
    for name in ("BASE", "FAILED", "READY"):
        assert validate_profile(make_profile(name), demo) == []


@pytest.mark.parametrize("history, code", [
    ((HistoryRecord("XX999", "passed", 8),), "UNKNOWN_COURSE"),
    ((HistoryRecord("CS101", "passed", 8), HistoryRecord("CS101", "failed", 3)), "DUPLICATE_HISTORY"),
    ((HistoryRecord("CS101", "passed", 4),), "GRADE_STATE_MISMATCH"),
    ((HistoryRecord("CS101", "failed", 6),), "GRADE_STATE_MISMATCH"),
])
def test_history_errors(demo, history, code):
    errors, _ = check_profile(make_profile(history=history), demo)
    assert code in codes(errors)


def test_unknown_goal_interest_and_exclusion(demo):
    profile = make_profile(career_goal_ids=("ASTRONAUT",), interest_ids=("COOKING",), excluded_course_ids=("ZZ1",))
    with pytest.raises(ProfileInvalid) as exc:
        validate_profile(profile, demo)
    assert {"UNKNOWN_GOAL", "UNKNOWN_INTEREST", "UNKNOWN_COURSE"} <= set(codes(exc.value.errors))


def test_pass_without_grade_does_not_satisfy(demo):
    profile = make_profile(history=(HistoryRecord("CS101", "passed", None),))
    _, warnings = check_profile(profile, demo)
    assert "PASS_WITHOUT_GRADE" in codes(warnings)
    assert satisfied_course_ids(profile) == set()


def test_failed_and_planned_do_not_satisfy():
    profile = make_profile(history=(HistoryRecord("MA101", "failed", 4), HistoryRecord("CS101", "planned")))
    assert satisfied_course_ids(profile) == set()


def test_pass_with_missing_ancestor_only_warns(demo):
    profile = make_profile(history=(HistoryRecord("ST201", "passed", 7),))
    errors, warnings = check_profile(profile, demo)
    assert errors == [] and "HISTORY_PREREQUISITE_GAP" in codes(warnings)
    assert "ST201" in satisfied_course_ids(profile)  # recorded pass is never rewritten
