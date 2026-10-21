"""Giả định what-if áp lên bản sao của dòng sinh viên (hợp đồng mục 6.6); không cần database."""
import re

import pandas as pd
import pytest

from src.recommender.whatif import apply_assumptions

COURSES = {"MAT2502", "MAT2505", "MAT2323", "MAT3533"}


def _student():
    return pd.Series({
        "student_id": 7, "curriculum_code": "HUS-7480113QTD-2022",
        "passed_courses": ["MAT2502"], "outstanding_courses": ["MAT2505"],
        "latest_scores": {"MAT2502": 7.0, "MAT2505": 3.0},
        "latest_attempts": {
            "MAT2502": {"term_code": "20242", "attempt_no": 1, "score": 7.0, "letter_grade": "B", "status": "passed"},
            "MAT2505": {"term_code": "20252", "attempt_no": 1, "score": 3.0, "letter_grade": "F", "status": "failed"},
        },
        "credits_earned": 4, "gpa": 3.0,
    })


def _apply(assumptions, student=None):
    return apply_assumptions(student if student is not None else _student(), assumptions, COURSES, 10.0, "20252")


def test_assuming_a_pass_clears_the_debt_and_becomes_the_latest_attempt():
    view = _apply([{"course_code": "MAT2505", "status": "passed", "score": 6.0}])
    assert "MAT2505" in view["passed_courses"] and "MAT2505" not in view["outstanding_courses"]
    assert view["latest_scores"]["MAT2505"] == 6.0
    assert view["latest_attempts"]["MAT2505"] == {"term_code": "20252", "attempt_no": 2, "score": 6.0,
                                                   "letter_grade": None, "status": "passed"}


def test_assuming_a_failure_turns_a_passed_course_into_a_debt():
    view = _apply([{"course_code": "MAT2502", "status": "failed", "score": 2.0}])
    assert "MAT2502" in view["outstanding_courses"] and "MAT2502" not in view["passed_courses"]
    assert view["latest_attempts"]["MAT2502"]["attempt_no"] == 2


def test_a_course_never_studied_starts_at_attempt_one():
    view = _apply([{"course_code": "MAT2323", "status": "passed", "score": 8.0}])
    assert view["latest_attempts"]["MAT2323"]["attempt_no"] == 1
    assert view["passed_courses"] == ["MAT2323", "MAT2502"], "danh sách phải sắp theo mã để tất định"


def test_a_score_can_be_left_out_and_then_counts_for_no_topic():
    view = _apply([{"course_code": "MAT2505", "status": "passed"}])
    assert "MAT2505" not in view["latest_scores"]
    assert view["latest_attempts"]["MAT2505"]["score"] is None


def test_the_original_row_is_never_modified():
    student = _student()
    _apply([{"course_code": "MAT2505", "status": "passed", "score": 6.0},
            {"course_code": "MAT2502", "status": "failed", "score": 1.0}], student)
    assert student["passed_courses"] == ["MAT2502"] and student["outstanding_courses"] == ["MAT2505"]
    assert student["latest_scores"] == {"MAT2502": 7.0, "MAT2505": 3.0}
    assert student["latest_attempts"]["MAT2505"]["attempt_no"] == 1


def test_credits_and_gpa_are_left_alone():
    view = _apply([{"course_code": "MAT2505", "status": "passed", "score": 6.0}])
    assert view["credits_earned"] == 4 and view["gpa"] == 3.0


def test_no_assumption_gives_an_equal_copy():
    view = _apply([])
    assert view.to_dict() == _student().to_dict()


@pytest.mark.parametrize(("assumption", "field"), [
    ({"course_code": "XYZ999", "status": "passed"}, "assumptions[0].course_code"),
    ({"course_code": "MAT2505", "status": "withdrawn"}, "assumptions[0].status"),
    ({"course_code": "MAT2505", "status": "passed", "score": -0.5}, "assumptions[0].score"),
    ({"course_code": "MAT2505", "status": "passed", "score": 10.5}, "assumptions[0].score"),
    ({"course_code": "MAT2505", "status": "passed", "score": "6"}, "assumptions[0].score"),
    ({"course_code": "MAT2505", "status": "passed", "score": True}, "assumptions[0].score"),
    ({"course_code": "MAT2505", "status": "passed", "score": float("nan")}, "assumptions[0].score"),
    ({"course_code": "MAT2505", "status": "passed", "grade": "A"}, "assumptions[0]"),
])
def test_an_invalid_assumption_names_the_field_that_is_wrong(assumption, field):
    with pytest.raises(ValueError, match="^" + re.escape(field)):
        _apply([assumption])


def test_the_same_course_cannot_be_assumed_twice():
    with pytest.raises(ValueError, match=r"^assumptions\[1\]\.course_code"):
        _apply([{"course_code": "MAT2505", "status": "passed"}, {"course_code": "MAT2505", "status": "failed"}])


def test_the_score_range_follows_the_grading_scheme_of_the_curriculum():
    """DEMO và HUS có thang điểm riêng (mục 6.2): không được viết cứng 10."""
    student = _student()
    assumption = [{"course_code": "MAT2505", "status": "passed", "score": 4.5}]
    assert apply_assumptions(student, assumption, COURSES, 4.5, "20252")["latest_scores"]["MAT2505"] == 4.5
    with pytest.raises(ValueError):
        apply_assumptions(student, [{"course_code": "MAT2505", "status": "passed", "score": 5.0}],
                          COURSES, 4.5, "20252")
