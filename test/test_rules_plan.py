"""Tests for validation of proposed study plans."""

import pandas as pd

from src.recommender import recommend
from src.rules.plan import check_plan


class _Repo:
    def __init__(self, courses, blocks=(), max_credits=20, min_credits=None):
        self.courses = pd.DataFrame(courses, columns=["course_code", "credits", "elective_block",
                                                   "prerequisite_groups", "counts_toward_total"])
        self.blocks = pd.DataFrame(blocks, columns=["block_code", "required_credits"])
        self.max_credits = max_credits
        self.min_credits = min_credits

    def curriculum_courses(self, _code):
        return self.courses

    def elective_blocks(self, _code):
        return self.blocks

    def curriculum(self, _code):
        result = {"max_credits_per_term": self.max_credits}
        return result


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


def test_minimum_credits_are_unconstrained_without_explicit_argument():
    courses = [_course("A", 4), _course("B", 3), _course("C", 5)]
    for codes in [["A"], ["A", "B"], ["A", "B", "C"]]:
        assert check_plan(_Repo(courses), _student(), codes) == []


def test_maximum_credit_limit_and_inclusive_boundary():
    courses = [_course("A", 4), _course("B", 3), _course("C", 5)]
    assert check_plan(_Repo(courses, max_credits=7, min_credits=1), _student(), ["A"]) == []
    assert check_plan(_Repo(courses, max_credits=7, min_credits=1), _student(), ["A", "B"]) == []
    assert check_plan(_Repo(courses, max_credits=7, min_credits=1), _student(), ["A", "B", "C"]) == [{
        "code": "credit_limit_exceeded", "course_code": "C",
        "data": {"max_credits_per_term": 7, "total_credits": 12},
    }]


def test_explicit_minimum_validates_empty_plan():
    result = check_plan(_Repo([]), _student(), [], min_credits=5)
    assert result == [{"code": "credit_below_minimum", "course_code": None,
                       "data": {"min_credits": 5, "total_credits": 0}}]


def test_optional_minimum_configuration_is_unconstrained_and_plan_is_not_mutated():
    plan = ["A", "B"]
    repo = _Repo([_course("A", 2), _course("B", 3)])
    assert check_plan(repo, _student(), plan) == []
    assert plan == ["A", "B"]



def test_explicit_maximum_overrides_curriculum_limit():
    repo = _Repo([_course("A", 4), _course("B", 3)], max_credits=20)
    assert check_plan(repo, _student(), ["A", "B"], max_credits=6) == [{
        "code": "credit_limit_exceeded", "course_code": "B",
        "data": {"max_credits": 6, "total_credits": 7},
    }]


def test_explicit_minimum_warning_is_last():
    repo = _Repo([_course("A", 4, groups=[["P"]])])
    result = check_plan(repo, _student(), ["A"], min_credits=5)
    assert result == [
        {"code": "missing_prerequisite", "course_code": "A",
         "data": {"missing_prerequisites": [["P"]]}},
        {"code": "credit_below_minimum", "course_code": None,
         "data": {"min_credits": 5, "total_credits": 4}},
    ]


def test_duplicate_course_credits_count_once_for_plan_limit():
    repo = _Repo([_course("A", 6)], max_credits=10)
    result = check_plan(repo, _student(), ["A", "A"], max_credits=10)
    assert [v for v in result if v["code"] == "credit_limit_exceeded"] == []
    assert check_plan(repo, _student(), ["A", "A"], min_credits=7)[-1]["data"]["total_credits"] == 6


def test_empty_plan_without_minimum_does_not_query_repository():
    class NoCalls:
        def __getattr__(self, name):
            raise AssertionError(f"repository queried through {name}")

    assert check_plan(NoCalls(), _student(), []) == []

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
    codes = [item["course_code"] for item in recommend(repo_all, student)["items"]]
    assert codes
    assert check_plan(repo_all, student, codes) == []
