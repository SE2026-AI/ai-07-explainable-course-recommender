"""T-05 Prerequisite validation — reference oracle BASE/FAILED/READY (Q-01)."""

from backend.domain import prerequisites as pre
from backend.domain.profile import failed_course_ids, satisfied_course_ids
from conftest import REFERENCE, make_profile


def _eval(catalog, name, cid, **kw):
    profile = make_profile(name)
    return pre.evaluate(catalog, satisfied_course_ids(profile), cid, failed=failed_course_ids(profile), **kw)


def test_base_eligible_set(demo):
    expected = REFERENCE["expected"]["BASE"]
    assert pre.eligible_now(demo, satisfied_course_ids(make_profile("BASE"))) == sorted(expected["eligible"])


def test_base_missing_prerequisites(demo):
    ai = _eval(demo, "BASE", "AI301")
    assert not ai.eligible and list(ai.direct_missing_prerequisite_ids) == REFERENCE["expected"]["BASE"]["AI301_missing"]
    assert ai.transitive_missing_paths == (("ST201", "AI301"),)
    dl = _eval(demo, "BASE", "DL401")
    assert list(dl.direct_missing_prerequisite_ids) == REFERENCE["expected"]["BASE"]["DL401_missing_direct"]
    assert dl.transitive_missing_paths == (("ST201", "AI301", "DL401"),)
    assert pre.TRANSITIVE_BLOCKED in dl.reason_codes


def test_failed_prerequisite_blocks(demo):
    st = _eval(demo, "FAILED", "ST201")
    assert st.eligible is REFERENCE["expected"]["FAILED"]["ST201_eligible"]
    assert st.direct_missing_prerequisite_ids == ("MA101",)


def test_failed_course_can_be_retaken(demo):
    ma = _eval(demo, "FAILED", "MA101")
    assert ma.eligible and pre.RETAKE in ma.reason_codes


def test_ready_profile(demo):
    assert _eval(demo, "READY", "AI301").eligible is REFERENCE["expected"]["READY"]["AI301_eligible"]
    assert _eval(demo, "READY", "DL401").eligible is REFERENCE["expected"]["READY"]["DL401_eligible"]


def test_completed_courses_not_recommendable(demo):
    cs = _eval(demo, "BASE", "CS101")
    assert not cs.eligible and cs.reason_codes == (pre.COMPLETED,)


def test_same_term_selection_does_not_unlock(demo):
    # Selecting/planning ST201 never satisfies AI301 within the same term.
    from backend.domain.profile import HistoryRecord
    profile = make_profile("BASE")
    planned = make_profile("BASE", history=profile.history + (HistoryRecord("ST201", "planned"),))
    assert not pre.evaluate(demo, satisfied_course_ids(planned), "AI301").eligible


def test_unlocks_and_offerings(demo):
    st = _eval(demo, "BASE", "ST201")
    assert st.unlocks == ("AI301",)  # CS101 already passed, so ST201 is the last gate
    blocked = _eval(demo, "BASE", "ST201", term_id="2030-SUMMER")
    assert not blocked.eligible and pre.NOT_OFFERED in blocked.reason_codes


def test_excluded_by_user(demo):
    profile = make_profile("BASE")
    r = pre.evaluate(demo, satisfied_course_ids(profile), "SE201", excluded={"SE201"})
    assert not r.eligible and pre.EXCLUDED_BY_USER in r.reason_codes
