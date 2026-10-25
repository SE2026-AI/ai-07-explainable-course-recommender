"""Tests for validation of proposed study plans."""

import pandas as pd

from src.recommender import recommend
from src.rules.plan import check_plan


class _Repo:
    def __init__(self, courses, blocks=(), max_credits=20):
        self.courses = pd.DataFrame(courses)
        self.blocks = pd.DataFrame(blocks, columns=["block_code", "required_credits"])
        self.max_credits = max_credits

    def curriculum_courses(self, _code):
        return self.courses

    def elective_blocks(self, _code):
        return self.blocks

    def curriculum(self, _code):
        return {"max_credits_per_term": self.max_credits}


def _course(code, credits=3, block=None, groups=None, counts=True):
    return {"course_code": code, "credits": credits, "elective_block": block,
            "prerequisite_groups": groups or [], "counts_toward_total": int(counts)}


def _student(passed=()):
    return {"curriculum_code": "C", "passed_courses": list(passed)}


def test_empty_plan_has_no_violations():
    assert check_plan(_Repo([]), _student(), []) == []


def test_credit_limit_reports_actual_total_and_configured_limit():
    repo = _Repo([_course("A", 6), _course("B", 5)], max_credits=10)
    assert check_plan(repo, _student(), ["A", "B"]) == [{
        "code": "credit_limit_exceeded", "course_code": "B",
        "data": {"max_credits_per_term": 10, "total_credits": 11},
    }]


def test_missing_prerequisite_preserves_and_or_groups_and_plan_does_not_unlock():
    repo = _Repo([_course("A"), _course("B"), _course("C", groups=[["A", "B"], ["P", "Q"]])])
    result = check_plan(repo, _student(), ["A", "C"])
    assert result == [{
        "code": "missing_prerequisite", "course_code": "C",
        "data": {"missing_prerequisites": [["A", "B"], ["P", "Q"]]},
    }]


def test_already_passed_and_not_in_curriculum_can_coexist():
    repo = _Repo([_course("DONE", groups=[["NEVER"]])])
    assert check_plan(repo, _student(["DONE", "OUTSIDE"]), ["DONE", "OUTSIDE"]) == [
        {"code": "already_passed", "course_code": "DONE", "data": {}},
        {"code": "missing_prerequisite", "course_code": "DONE",
         "data": {"missing_prerequisites": [["NEVER"]]}},
        {"code": "already_passed", "course_code": "OUTSIDE", "data": {}},
        {"code": "not_in_curriculum", "course_code": "OUTSIDE", "data": {}},
    ]


def test_duplicate_course_is_reported_for_each_occurrence_after_first():
    repo = _Repo([_course("A")])
    assert check_plan(repo, _student(), ["A", "A", "A"]) == [
        {"code": "duplicate_course", "course_code": "A", "data": {"occurrence": 2}},
        {"code": "duplicate_course", "course_code": "A", "data": {"occurrence": 3}},
    ]


def test_elective_block_limit_accounts_for_passed_credits_and_non_divisible_limit():
    repo = _Repo([_course("E1", 2, "OPT"), _course("E2", 4, "OPT"), _course("E3", 3, "OPT")],
                 [("OPT", 5)])
    result = check_plan(repo, _student(["E1"]), ["E2", "E3"])
    assert result == [{
        "code": "block_limit_exceeded", "course_code": "E2",
        "data": {"block_code": "OPT", "required_credits": 5, "earned_credits": 2,
                 "planned_credits": 0, "course_credits": 4, "total_credits": 6},
    }, {
        "code": "block_limit_exceeded", "course_code": "E3",
        "data": {"block_code": "OPT", "required_credits": 5, "earned_credits": 2,
                 "planned_credits": 4, "course_credits": 3, "total_credits": 9},
    }]


def test_non_counting_block_courses_do_not_add_to_term_total():
    repo = _Repo([_course("A", 8), _course("X", 8, counts=False)], max_credits=8)
    assert check_plan(repo, _student(), ["A", "X"]) == []


def test_passed_elective_in_plan_is_not_counted_twice_for_its_block():
    repo = _Repo([_course("E", 5, "OPT"), _course("NEXT", 3, "OPT")], [("OPT", 5)])
    assert check_plan(repo, _student(["E"]), ["E", "NEXT"]) == [
        {"code": "already_passed", "course_code": "E", "data": {}},
        {"code": "block_limit_exceeded", "course_code": "NEXT",
         "data": {"block_code": "OPT", "required_credits": 5, "earned_credits": 5,
                  "planned_credits": 0, "course_credits": 3, "total_credits": 8}},
    ]


def test_multiple_violations_and_order_follow_plan_then_code():
    repo = _Repo([_course("A", 8, groups=[["P"]]), _course("B", 8)], max_credits=10)
    result = check_plan(repo, _student(["A"]), ["A", "B"])
    assert [(v["course_code"], v["code"]) for v in result] == [
        ("A", "already_passed"), ("A", "missing_prerequisite"), ("B", "credit_limit_exceeded"),
    ]


def test_recommendations_are_valid_plans(repo_all):
    students = repo_all.students()
    student = students[(students["university_code"] == "DEMO")
                       & (students["student_code"] == "T01")].iloc[0]
    codes = [item["course_code"] for item in recommend(repo_all, student)]
    assert codes
    assert check_plan(repo_all, student, codes) == []
