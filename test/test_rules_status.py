"""Contract and golden-data tests for course status classification."""

import pandas as pd
import pytest

from src.rules.status import course_status

EXPECTED_PATH = "test/fixtures/students/expected_course_status.csv"
EXPECTED = pd.read_csv(EXPECTED_PATH)
CASES = list(EXPECTED[["university_code", "student_code", "curriculum_code"]]
             .drop_duplicates().itertuples(index=False, name=None))


@pytest.mark.parametrize("university_code,student_code,curriculum_code", CASES)
def test_course_status_matches_golden_data(repo_all, university_code, student_code, curriculum_code):
    students = repo_all.students()
    student = students[(students["university_code"] == university_code)
                       & (students["student_code"] == student_code)].iloc[0]
    assert student["curriculum_code"] == curriculum_code
    actual = course_status(repo_all, student)
    expected_rows = EXPECTED[(EXPECTED["university_code"] == university_code)
                             & (EXPECTED["student_code"] == student_code)]
    expected = dict(zip(expected_rows["course_code"], expected_rows["expected_status"]))
    differences = [f"{code}: expected {expected.get(code)!r}, actual {actual.get(code)!r}"
                   for code in sorted(set(expected) | set(actual)) if expected.get(code) != actual.get(code)]
    assert not differences, f"{university_code}/{student_code}: " + "; ".join(differences)


@pytest.mark.parametrize("university_code,student_code,curriculum_code", CASES)
def test_statuses_cover_all_curriculum_courses(repo_all, university_code, student_code, curriculum_code):
    student = repo_all.students()
    student = student[(student["university_code"] == university_code)
                      & (student["student_code"] == student_code)].iloc[0]
    courses = repo_all.curriculum_courses(curriculum_code)
    actual = course_status(repo_all, student)
    ids = set(courses["course_code"])
    assert set(actual) == ids
    assert len(actual) == len(courses)
    assert all(status in {"passed", "block_complete", "missing_prerequisite", "retake", "eligible"}
               for status in actual.values())
    passed = set(student["passed_courses"])
    for _, course in courses.iterrows():
        if actual[course["course_code"]] == "eligible":
            assert all(set(group) & passed for group in course["prerequisite_groups"]), \
                f"{university_code}/{student_code}/{course['course_code']} has an unsatisfied prerequisite group"


class _Repo:
    def __init__(self, courses, electives=()):
        self.courses = pd.DataFrame(courses)
        self.electives = pd.DataFrame(electives, columns=["block_code", "required_credits"])

    def curriculum_courses(self, _):
        return self.courses

    def elective_blocks(self, _):
        return self.electives


def _course(code, credits=3, block=None, groups=None):
    return {"course_code": code, "credits": credits, "elective_block": block,
            "prerequisite_groups": groups or []}


@pytest.mark.parametrize(("earned", "expected"), [(3, "eligible"), (6, "block_complete"), (9, "block_complete")])
def test_elective_completion_uses_passed_credits_and_threshold(earned, expected):
    courses = [_course("OPT1"), _course("OPT2"), _course("OPT3"), _course("OPT4"), _course("CORE", block=None)]
    repo = _Repo(courses, [("E", 6)])
    repo.courses.loc[:3, "elective_block"] = "E"
    result = course_status(repo, {"curriculum_code": "C", "passed_courses": ["OPT1"] if earned == 3
                                 else ["OPT1", "OPT2"] if earned == 6 else ["OPT1", "OPT2", "OPT3"],
                                 "outstanding_courses": []})
    assert result["OPT4"] == expected
    assert result["CORE"] == "eligible"


def test_prerequisites_are_and_between_groups_and_or_within_groups():
    repo = _Repo([_course("A"), _course("B"), _course("C", groups=[["A", "B"], ["A"]])])
    student = {"curriculum_code": "C", "passed_courses": ["B"], "outstanding_courses": []}
    assert course_status(repo, student)["C"] == "missing_prerequisite"
    student["passed_courses"] = ["B", "A"]
    assert course_status(repo, student)["C"] == "eligible"


def test_precedence_preserves_passed_and_block_complete_over_prerequisite_and_retake():
    repo = _Repo([_course("DONE", groups=[["NEVER"]]), _course("OPT1"),
                  _course("OPT2", groups=[["NEVER"]])], [("E", 3)])
    repo.courses.loc[1:, "elective_block"] = "E"
    result = course_status(repo, {"curriculum_code": "C", "passed_courses": ["DONE", "OPT1"],
                                  "outstanding_courses": ["OPT2"]})
    assert result == {"DONE": "passed", "OPT1": "passed", "OPT2": "block_complete"}


def test_missing_prerequisite_precedes_retake():
    repo = _Repo([_course("R", groups=[["P"]])])
    result = course_status(repo, {"curriculum_code": "C", "passed_courses": [], "outstanding_courses": ["R"]})
    assert result["R"] == "missing_prerequisite"
