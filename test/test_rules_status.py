"""Contract and golden-data tests for course status classification."""

from collections import Counter

import pandas as pd
import pytest

from src.rules.status import course_status, course_status_details, elective_credits_passed, fits_in_block

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


def test_status_details_invariants_hold_for_all_synthetic_students(repo_all):
    students = repo_all.students()
    synthetic = students[students["is_synthetic"].astype(bool)]
    # The demo fixture also has synthetic students; this sweep is specifically over
    # the 200 records loaded from data/synthetic/students.csv.
    synthetic = synthetic[synthetic["student_code"].astype(str).str.fullmatch(r"\d{8}")]
    assert len(synthetic) == 200

    class _CachedRepo:
        def __init__(self, repository):
            self.repository = repository
            self.courses = {}
            self.results = repository.course_results()

        def curriculum_courses(self, curriculum_code):
            if curriculum_code not in self.courses:
                self.courses[curriculum_code] = self.repository.curriculum_courses(curriculum_code)
            return self.courses[curriculum_code]

        def elective_blocks(self, curriculum_code):
            return self.repository.elective_blocks(curriculum_code)

        def course_results(self, student_id):
            return self.results[self.results["student_id"] == student_id]

    status_repo = _CachedRepo(repo_all)
    courses_by_curriculum = {}
    for _, student in synthetic.iterrows():
        curriculum_code = student["curriculum_code"]
        if curriculum_code not in courses_by_curriculum:
            courses_by_curriculum[curriculum_code] = status_repo.curriculum_courses(curriculum_code)
        courses = courses_by_curriculum[curriculum_code]
        codes = courses["course_code"].tolist()
        details = course_status_details(status_repo, student)
        assert len(codes) == len(set(codes))
        assert len(details) == len(codes)
        assert set(details) == set(codes)
        statuses = Counter(item["status"] for item in details.values())
        assert set(statuses) <= {"passed", "block_complete", "missing_prerequisite", "retake", "eligible"}
        assert statuses.total() == len(courses)
        passed = set(student["passed_courses"])
        by_code = courses.set_index("course_code")
        for code, detail in details.items():
            status = detail["status"]
            groups = by_code.loc[code, "prerequisite_groups"]
            if status == "eligible":
                assert all(set(group) & passed for group in groups), (student["student_code"], code)
            elif status == "missing_prerequisite":
                expected_missing = [list(group) for group in groups if not (set(group) & passed)]
                assert detail["missing_prerequisites"] == expected_missing
                assert expected_missing
            elif status == "passed":
                assert code in passed
            elif status == "block_complete":
                assert detail["block"]["earned_credits"] >= detail["block"]["required_credits"]
        # course_status_details has no summary object: each curriculum course has
        # exactly one status, so the status counts must total the curriculum size.
        assert sum(Counter(item["status"] for item in details.values()).values()) == len(courses)


def test_status_details_invariants_hold_for_demo_fixture(repo_all):
    students = repo_all.students()
    demo = students[students["university_code"] == "DEMO"]
    assert not demo.empty
    for _, student in demo.iterrows():
        courses = repo_all.curriculum_courses(student["curriculum_code"])
        details = course_status_details(repo_all, student)
        assert set(details) == set(courses["course_code"])
        assert len(details) == len(courses)
        passed = set(student["passed_courses"])
        for _, course in courses.iterrows():
            status = details[course["course_code"]]["status"]
            if status == "eligible":
                assert all(set(group) & passed for group in course["prerequisite_groups"])
            elif status == "missing_prerequisite":
                expected_missing = [list(group) for group in course["prerequisite_groups"]
                                    if not (set(group) & passed)]
                assert details[course["course_code"]]["missing_prerequisites"] == expected_missing
                assert expected_missing
            elif status == "passed":
                assert course["course_code"] in passed
            elif status == "block_complete":
                block = details[course["course_code"]]["block"]
                assert block["earned_credits"] >= block["required_credits"]


def test_fairness_group_does_not_change_academic_status(repo_all):
    student = repo_all.students().iloc[0].to_dict()
    first = {**student, "fairness_group": "group_a"}
    second = {**student, "fairness_group": "group_b"}
    assert {k: v for k, v in first.items() if k != "fairness_group"} == {
        k: v for k, v in second.items() if k != "fairness_group"
    }
    assert course_status_details(repo_all, first) == course_status_details(repo_all, second)


class _Repo:
    def __init__(self, courses, electives=()):
        self.courses = pd.DataFrame(courses)
        self.electives = pd.DataFrame(electives, columns=["block_code", "required_credits"])
        self.electives["block_name"] = ""

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


def test_status_details_keep_only_unsatisfied_prerequisite_groups():
    repo = _Repo([_course("C", groups=[["A", "B"], ["D"], ["G", "F"]]),
                  _course("A"), _course("D"), _course("E")])
    student = {"curriculum_code": "C", "passed_courses": ["A", "E"], "outstanding_courses": []}
    details = course_status_details(repo, student)
    assert details["C"] == {
        "status": "missing_prerequisite",
        "missing_prerequisites": [["D"], ["G", "F"]],
    }
    assert "D" not in student["passed_courses"]


def test_details_include_elective_block_credit_progress():
    courses = [_course("OPT1", credits=3), _course("OPT2", credits=3), _course("OPT3", credits=3)]
    repo = _Repo(courses, [("E", 5)])
    repo.courses["elective_block"] = "E"
    details = course_status_details(repo, {
        "curriculum_code": "C", "passed_courses": ["OPT1", "OPT2"], "outstanding_courses": [],
    })
    assert details["OPT3"] == {
        "status": "block_complete",
        "block": {"block_code": "E", "block_name": "", "required_credits": 5, "earned_credits": 6},
    }


@pytest.mark.parametrize(
    ("block_code", "required", "credits", "passed", "expected_earned", "expected_status"),
    [
        ("II", 5, [2, 3], ["II1", "II2"], 5, "passed"),
        ("II", 5, [2, 3], ["II1"], 2, "eligible"),
        ("V.3", 7, [3, 4, 7], ["V.31", "V.32"], 7, "block_complete"),
        ("V.3", 7, [3, 4, 7], ["V.33"], 7, "block_complete"),
    ],
)
def test_non_divisible_elective_credit_thresholds(
    block_code, required, credits, passed, expected_earned, expected_status
):
    codes = [f"{block_code}{index}" for index in range(1, len(credits) + 1)]
    courses = [_course(code, credit, block_code) for code, credit in zip(codes, credits, strict=True)]
    repo = _Repo(courses, [(block_code, required)])
    details = course_status_details(repo, {
        "curriculum_code": "C", "passed_courses": passed, "outstanding_courses": [],
    })
    if expected_status == "passed":
        assert all(details[code]["status"] == "passed" for code in codes)
        assert sum(credits) == expected_earned
    else:
        unpassed = next(code for code in codes if code not in passed)
        assert details[unpassed]["status"] == expected_status
        assert elective_credits_passed(repo.courses, passed)[block_code] == expected_earned
        if expected_status == "block_complete":
            assert details[unpassed]["block"]["earned_credits"] >= required
        else:
            assert "block" not in details[unpassed]


def test_student_without_academic_results_has_valid_unpassed_statuses():
    repo = _Repo([_course("A"), _course("B", groups=[["A"]])])
    details = course_status_details(repo, {
        "curriculum_code": "C", "passed_courses": [], "outstanding_courses": [],
    })
    assert details == {
        "A": {"status": "eligible"},
        "B": {"status": "missing_prerequisite", "missing_prerequisites": [["A"]]},
    }
    assert all(value["status"] != "passed" for value in details.values())


def test_student_who_passed_entire_curriculum_has_consistent_statuses():
    repo = _Repo([_course("A"), _course("B", 2, "E"), _course("C", 3, "E")], [("E", 5)])
    details = course_status_details(repo, {
        "curriculum_code": "C", "passed_courses": ["A", "B", "C"], "outstanding_courses": [],
    })
    assert set(details) == {"A", "B", "C"}
    assert all(detail == {"status": "passed"} for detail in details.values())
    assert sum(detail["status"] == "passed" for detail in details.values()) == len(repo.courses)
    earned_by_block = elective_credits_passed(repo.courses, ["A", "B", "C"])
    required_by_block = dict(zip(repo.electives["block_code"], repo.electives["required_credits"], strict=True))
    assert all(earned_by_block[block] >= required for block, required in required_by_block.items())


def test_nonpositive_year_of_study_with_future_cohort_does_not_break_status(repo_all):
    student = repo_all.students().iloc[0].to_dict()
    baseline = course_status_details(repo_all, student)
    for year in (0, -1):
        boundary = {**student, "year_of_study": year, "cohort_year": 9999}
        assert course_status_details(repo_all, boundary) == baseline


def test_shared_elective_credit_and_block_fit_helpers():
    courses = pd.DataFrame([_course("A", 3, "X"), _course("B", 4, "X"),
                            _course("C", 2, "Y"), _course("CORE", 3)])
    assert elective_credits_passed(courses, ["A", "CORE", "UNKNOWN"]) == {"X": 3, "Y": 0}
    assert elective_credits_passed(courses, []) == {"X": 0, "Y": 0}
    assert fits_in_block(3, 2, 5)
    assert not fits_in_block(4, 2, 5)
    assert fits_in_block(0, 5, 5)


def test_attempt_details_cover_passed_retake_and_exempt_courses():
    repo = _Repo([_course("P"), _course("R"), _course("X")])
    repo.course_results = lambda _student_id: pd.DataFrame([
        {"course_code": "P", "term_code": "20251", "attempt_no": 2,
         "score": 8.0, "letter_grade": "B", "status": "passed", "recency": 1},
        {"course_code": "R", "term_code": "20252", "attempt_no": 1,
         "score": 3.0, "letter_grade": "F", "status": "failed", "recency": 1},
        {"course_code": "X", "term_code": "20251", "attempt_no": 1,
         "score": None, "letter_grade": None, "status": "exempted", "recency": 1},
    ])
    details = course_status_details(repo, {
        "student_id": 1, "curriculum_code": "C", "passed_courses": ["P", "X"],
        "outstanding_courses": ["R"],
    })
    assert details["P"]["last_attempt"] == {
        "term_code": "20251", "attempt_no": 2, "score": 8.0, "letter_grade": "B",
    }
    assert details["R"]["status"] == "retake"
    assert details["R"]["last_attempt"]["score"] == 3.0
    assert details["X"]["last_attempt"] == {
        "term_code": "20251", "attempt_no": 1, "score": None, "letter_grade": None,
    }


def test_detailed_status_matches_legacy_status_for_golden_students(repo_all):
    students = repo_all.students()
    for university_code, student_code, curriculum_code in CASES:
        student = students[(students["university_code"] == university_code)
                           & (students["student_code"] == student_code)].iloc[0]
        details = course_status_details(repo_all, student)
        assert {code: value["status"] for code, value in details.items()} == course_status(repo_all, student)
        assert student["curriculum_code"] == curriculum_code
        for code, value in details.items():
            if value["status"] == "missing_prerequisite":
                assert value["missing_prerequisites"]
                assert all(not (set(group) & set(student["passed_courses"]))
                           for group in value["missing_prerequisites"])
            if value["status"] == "block_complete":
                assert value["block"]["earned_credits"] >= value["block"]["required_credits"]


def test_details_return_attempt_information_and_exemption_nulls(repo_all):
    students = repo_all.students()
    student = students[(students["university_code"] == "HUS") & (students["student_code"] == "T04")].iloc[0]
    details = course_status_details(repo_all, student)
    assert details["MAT2505"]["last_attempt"] == {
        "term_code": "20251", "attempt_no": 2, "score": 6.0, "letter_grade": "C",
    }

    retaker = students[(students["university_code"] == "HUS") & (students["student_code"] == "T03")].iloc[0]
    retake_details = course_status_details(repo_all, retaker)
    assert retake_details["MAT2505"]["status"] == "retake"
    assert retake_details["MAT2505"]["last_attempt"] == {
        "term_code": "20252", "attempt_no": 1, "score": 3.0, "letter_grade": "F",
    }

    exempt = students[(students["university_code"] == "HUS") & (students["student_code"] == "T15")].iloc[0]
    exempt_details = course_status_details(repo_all, exempt)
    assert exempt_details["FLF1107"]["last_attempt"]["score"] is None
    assert exempt_details["FLF1107"]["last_attempt"]["letter_grade"] is None
