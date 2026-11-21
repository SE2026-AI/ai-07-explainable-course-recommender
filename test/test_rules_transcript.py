"""Pure transcript construction tests and compatibility checks against repository data."""

from copy import deepcopy

import pandas as pd
import pytest

from src.rules.status import course_status
from src.rules.transcript import build_student


def _inputs(pass_score=5.0, max_score=10.0):
    curriculum = {"university_code": "U", "curriculum_code": "C", "pass_score": pass_score,
                  "max_score": max_score, "total_credits": 9, "max_credits_per_term": 20}
    courses = pd.DataFrame([
        {"course_code": "A", "credits": 3, "block_code": "CORE", "block_required_credits": 6,
         "counts_toward_total": 1, "prerequisite_groups": []},
        {"course_code": "B", "credits": 3, "block_code": "CORE", "block_required_credits": 6,
         "counts_toward_total": 1, "prerequisite_groups": [["A"]]},
        {"course_code": "X", "credits": 2, "block_code": "EXTRA", "block_required_credits": 2,
         "counts_toward_total": 0, "prerequisite_groups": []},
    ])
    conversions = pd.DataFrame([
        {"letter": "A", "min_score": 8, "max_score": 10, "grade_point": 4.0, "is_pass": 1},
        {"letter": "C", "min_score": 5, "max_score": 7.9, "grade_point": 2.0, "is_pass": 1},
        {"letter": "F", "min_score": 0, "max_score": 4.9, "grade_point": 0.0, "is_pass": 0},
    ])
    return curriculum, courses, conversions


def _build(results, done=2, pass_score=5.0):
    return build_student(*_inputs(pass_score), done, results)


def _semester_number(term, admission):
    """Normalize main terms from admission; term 3 shares term 2's semester."""
    ordinal = 2 * (int(term["start_year"]) - int(admission["start_year"])) + min(int(term["term_no"]), 2)
    admission_ordinal = min(int(admission["term_no"]), 2)
    return ordinal - admission_ordinal + 1


def test_builds_repository_compatible_student_and_calculates_progress():
    student = _build([{"course_code": "A", "semester": 1, "score": 8.5},
                      {"course_code": "B", "semester": 2, "score": 3.0},
                      {"course_code": "X", "semester": 2, "score": 9.0}])
    assert student["student_id"] is None
    assert student["university_code"] == "U" and student["curriculum_code"] == "C"
    assert student["target_semester"] == 3
    assert student["passed_courses"] == ["A", "X"]
    assert student["outstanding_courses"] == ["B"]
    assert student["latest_scores"] == {"A": 8.5, "B": 3.0, "X": 9.0}
    assert student["latest_attempts"]["A"] == {
        "semester": 1, "score": 8.5, "letter_grade": "A", "grade_point": 4.0, "status": "passed"}
    assert student["credits_earned"] == student["credits_outstanding"] == 3
    assert student["gpa"] == 2.0
    assert student["block_progress"]["CORE"]["earned_credits"] == 3
    assert student["block_progress"]["EXTRA"]["earned_credits"] == 2


def test_curriculum_series_name_supplies_curriculum_code():
    _, courses, conversions = _inputs()
    curriculum = pd.Series({"university_code": "U", "pass_score": 5.0, "max_score": 10.0}, name="C")
    student = build_student(curriculum, courses, conversions, 0, [])
    assert student["curriculum_code"] == "C"


def test_missing_curriculum_code_is_rejected():
    curriculum, courses, conversions = _inputs()
    curriculum.pop("curriculum_code")
    with pytest.raises(ValueError, match="curriculum.curriculum_code:"):
        build_student(curriculum, courses, conversions, 0, [])


def test_pass_threshold_is_curriculum_specific_and_gpa_includes_failures():
    student = _build([{"course_code": "A", "semester": 1, "score": 6.0}], pass_score=6.0)
    assert student["passed_courses"] == ["A"]
    assert student["gpa"] == 2.0


def test_gpa_is_credit_weighted():
    curriculum, courses, conversions = _inputs()
    courses.loc[courses.course_code == "A", "credits"] = 12
    courses.loc[courses.course_code == "B", "credits"] = 2
    student = build_student(curriculum, courses, conversions, 1, [
        {"course_code": "A", "semester": 1, "score": 8},
        {"course_code": "B", "semester": 1, "score": 3},
    ])
    assert student["gpa"] == 3.43


def test_null_grade_point_credit_stays_in_gpa_denominator():
    curriculum, courses, conversions = _inputs()
    conversions.loc[conversions.letter == "C", "grade_point"] = None
    student = build_student(curriculum, courses, conversions, 1, [
        {"course_code": "A", "semester": 1, "score": 8},
        {"course_code": "B", "semester": 1, "score": 6},
    ])
    # Repository SQL sums the known 4.0 * 3 points, then divides by credits for both courses.
    assert student["gpa"] == 2.0

    only_null_grade_point = build_student(curriculum, courses, conversions, 1, [
        {"course_code": "B", "semester": 1, "score": 6},
    ])
    assert only_null_grade_point["gpa"] is None


def test_exempted_course_adds_credits_but_not_gpa_weight():
    student = _build([{"course_code": "A", "semester": 1, "score": 8},
                      {"course_code": "B", "semester": 1, "exempted": True}], done=1)
    assert student["passed_courses"] == ["A", "B"]
    assert student["credits_earned"] == 6
    assert student["gpa"] == 4.0


def test_semester_normalization_groups_summer_and_offsets_later_admission():
    term_2 = {"start_year": 2025, "term_no": 2}
    summer = {"start_year": 2025, "term_no": 3}
    next_term_1 = {"start_year": 2026, "term_no": 1}
    assert _semester_number(term_2, {"start_year": 2025, "term_no": 1}) == 2
    assert _semester_number(summer, {"start_year": 2025, "term_no": 1}) == 2
    assert _semester_number(term_2, term_2) == 1
    assert _semester_number(summer, term_2) == 1
    assert _semester_number(next_term_1, term_2) == 2


def test_exempted_and_empty_transcripts():
    exempted = _build([{"course_code": "A", "semester": 1, "exempted": True}])
    assert exempted["passed_courses"] == ["A"]
    assert exempted["credits_earned"] == 3
    assert exempted["gpa"] is None
    empty = _build([], done=0)
    assert empty["passed_courses"] == [] and empty["latest_attempts"] == {}
    assert empty["credits_earned"] == empty["credits_outstanding"] == 0
    assert empty["gpa"] is None


@pytest.mark.parametrize(("results", "done", "field", "message"), [
    ([{"course_code": "Q", "semester": 1, "score": 5}], 1, "course_code", "không tồn tại"),
    ([{"course_code": "A", "semester": 1, "score": 5}, {"course_code": "A", "semester": 1, "score": 6}], 1,
     "course_code", "trùng"),
    ([{"course_code": "A", "semester": 0, "score": 5}], 1, "semester", "phải từ"),
    ([{"course_code": "A", "semester": 2, "score": 5}], 1, "semester", "phải từ"),
    ([{"course_code": "A", "semester": "1", "score": 5}], 1, "semester", "số nguyên"),
    ([{"course_code": "A", "semester": 1, "score": -1}], 1, "score", "ngoài phạm vi"),
    ([{"course_code": "A", "semester": 1, "score": 11}], 1, "score", "ngoài phạm vi"),
    ([{"course_code": "A", "semester": 1}], 1, "results[0]", "điểm số"),
    ([{"course_code": "A", "semester": 1, "score": 5, "exempted": True}], 1, "results[0]", "điểm số"),
    ([{"course_code": "A", "semester": 1, "exempted": False}], 1, "exempted", "true"),
    ([{"course_code": "A", "semester": 1, "score": True}], 1, "score", "phải là số"),
])
def test_invalid_results_raise_field_path_value_errors(results, done, field, message):
    with pytest.raises(ValueError, match=field.replace("[", r"\[").replace("]", r"\]").replace(".", r"\.")) as exc:
        _build(results, done)
    assert message in str(exc.value)


@pytest.mark.parametrize("done", [-1, 13, 1.5, True])
def test_invalid_semesters_completed(done):
    with pytest.raises(ValueError, match="semesters_completed:"):
        _build([], done)


def test_nonempty_transcript_requires_completed_semester():
    with pytest.raises(ValueError, match="semesters_completed:"):
        _build([{"course_code": "A", "semester": 1, "score": 5}], 0)


def test_warnings_are_structured_and_do_not_change_pass_outcomes():
    curriculum, courses, conversions = _inputs()
    courses.at[courses.index[courses.course_code == "B"][0], "prerequisite_groups"] = [["NOPE"], ["A"]]
    student = build_student(curriculum, courses, conversions, 3, [
        {"course_code": "A", "semester": 2, "score": 8},
        {"course_code": "B", "semester": 1, "score": 8},
    ])
    assert student["passed_courses"] == ["A", "B"]
    assert student["warnings"] == [
        {"code": "prerequisite_not_in_transcript", "course_code": "B",
         "data": {"missing_prerequisites": [["NOPE"]]}},
        {"code": "studied_before_prerequisite", "course_code": "B",
         "data": {"semester": 1, "prerequisite_code": "A", "prerequisite_semester": 2}},
    ]
    assert all(set(warning) == {"code", "course_code", "data"} for warning in student["warnings"])


def test_or_prerequisite_group_satisfied_by_earlier_alternative():
    curriculum, courses, conversions = _inputs()
    courses = pd.concat([courses, pd.DataFrame([{
        "course_code": "C", "credits": 3, "block_code": "CORE", "block_required_credits": 6,
        "counts_toward_total": 1, "prerequisite_groups": [["A", "B"]],
    }])], ignore_index=True)
    student = build_student(curriculum, courses, conversions, 3, [
        {"course_code": "A", "semester": 1, "score": 8},
        {"course_code": "C", "semester": 2, "score": 8},
        {"course_code": "B", "semester": 3, "score": 8},
    ])
    assert not [warning for warning in student["warnings"]
                if warning["code"] == "studied_before_prerequisite" and warning["course_code"] == "C"]


def test_or_prerequisite_warning_selects_earliest_passed_course():
    curriculum, courses, conversions = _inputs()
    courses = pd.concat([courses, pd.DataFrame([{
        "course_code": "C", "credits": 3, "block_code": "CORE", "block_required_credits": 6,
        "counts_toward_total": 1, "prerequisite_groups": [["A", "X"]],
    }])], ignore_index=True)
    student = build_student(curriculum, courses, conversions, 3, [
        {"course_code": "C", "semester": 1, "score": 8},
        {"course_code": "A", "semester": 2, "score": 8},
        {"course_code": "X", "semester": 3, "score": 8},
    ])
    warning = next(w for w in student["warnings"]
                   if w["code"] == "studied_before_prerequisite" and w["course_code"] == "C")
    assert warning["data"]["prerequisite_code"] == "A"


def test_or_prerequisite_same_or_later_pass_still_warns():
    curriculum, courses, conversions = _inputs()
    courses = pd.concat([courses, pd.DataFrame([{
        "course_code": "C", "credits": 3, "block_code": "CORE", "block_required_credits": 6,
        "counts_toward_total": 1, "prerequisite_groups": [["A", "X"]],
    }])], ignore_index=True)
    student = build_student(curriculum, courses, conversions, 2, [
        {"course_code": "C", "semester": 1, "score": 8},
        {"course_code": "A", "semester": 1, "score": 8},
        {"course_code": "X", "semester": 2, "score": 8},
    ])
    warning = next(w for w in student["warnings"]
                   if w["code"] == "studied_before_prerequisite" and w["course_code"] == "C")
    assert warning["data"] == {"semester": 1, "prerequisite_code": "A", "prerequisite_semester": 1}


def test_inputs_are_not_mutated():
    curriculum, courses, conversions = _inputs()
    results = [{"course_code": "A", "semester": 1, "score": 8}]
    before = deepcopy((curriculum, courses, conversions, results))
    build_student(curriculum, courses, conversions, 1, results)
    pd.testing.assert_frame_equal(courses, before[1])
    pd.testing.assert_frame_equal(conversions, before[2])
    assert (curriculum, results) == (before[0], before[3])


def test_reconstruction_matches_all_200_synthetic_students(repo):
    students = repo.students()
    students = students[students["is_synthetic"].astype(bool)
                        & students["student_code"].astype(str).str.fullmatch(r"\d{8}")]
    assert len(students) == 200
    term_cache = {}
    course_cache = {}
    conversion_cache = {}
    program_rows = pd.read_csv("data/synthetic/student_programs.csv", dtype={"student_code": str,
                                                                               "admission_term_code": str})
    admission_terms = program_rows.set_index("student_code")["admission_term_code"].to_dict()
    for _, original in students.iterrows():
        curriculum_code = original["curriculum_code"]
        university = original["university_code"]
        if curriculum_code not in course_cache:
            course_cache[curriculum_code] = repo.curriculum_courses(curriculum_code)
            conversion_cache[curriculum_code] = repo.grade_conversions(curriculum_code)
        if university not in term_cache:
            term_cache[university] = repo.terms(university).sort_values("term_code")
        terms = term_cache[university]
        admission_code = admission_terms[str(original["student_code"])]
        admission = terms[terms["term_code"].astype(str) == admission_code]
        assert len(admission) == 1, f"{original['student_code']}: admission term {admission_code!r} missing"
        admission = admission.iloc[0]
        term_semester = {}
        for _, term in terms.iterrows():
            term_semester[str(term["term_code"])] = _semester_number(term, admission)

        results = []
        for code, attempt in original["latest_attempts"].items():
            semester = term_semester[str(attempt["term_code"])]
            assert 1 <= semester <= 12, (
                f"{original['student_code']}/{code}: term {attempt['term_code']} normalized to invalid "
                f"semester {semester} from admission {admission_code}"
            )
            if attempt["status"] == "exempted":
                result = {"course_code": code, "semester": semester, "exempted": True}
            else:
                result = {"course_code": code, "semester": semester, "score": float(attempt["score"])}
            results.append(result)
        done = max((result["semester"] for result in results), default=0)
        rebuilt = build_student(repo.curriculum(curriculum_code), course_cache[curriculum_code],
                                conversion_cache[curriculum_code], done, results)
        assert rebuilt["passed_courses"] == sorted(original["passed_courses"]), original["student_code"]
        assert rebuilt["outstanding_courses"] == sorted(original["outstanding_courses"]), original["student_code"]
        assert rebuilt["credits_earned"] == int(original["credits_earned"]), original["student_code"]
        assert rebuilt["credits_outstanding"] == int(original["credits_outstanding"]), original["student_code"]
        expected_gpa = None if pd.isna(original["gpa"]) else round(float(original["gpa"]), 2)
        assert rebuilt["gpa"] == expected_gpa, original["student_code"]
        assert rebuilt["latest_scores"] == original["latest_scores"], original["student_code"]
        expected_attempts = {
            code: {"semester": term_semester[str(attempt["term_code"])], "score": attempt["score"],
                   "letter_grade": attempt["letter_grade"], "status": attempt["status"]}
            for code, attempt in original["latest_attempts"].items()
        }
        actual_attempts = {
            code: {key: attempt[key] for key in ("semester", "score", "letter_grade", "status")}
            for code, attempt in rebuilt["latest_attempts"].items()
        }
        assert actual_attempts == expected_attempts, original["student_code"]
        repository_blocks = repo.block_progress(int(original["student_id"])).set_index("block_code")
        for block_code, progress in rebuilt["block_progress"].items():
            expected = repository_blocks.loc[block_code]
            assert progress["required_credits"] == int(expected["required_credits"]), (
                original["student_code"], block_code)
            assert progress["earned_credits"] == int(expected["earned_credits"]), (
                original["student_code"], block_code)
            assert progress["counts_toward_total"] == bool(expected["counts_toward_total"]), (
                original["student_code"], block_code)
        assert course_status(repo, rebuilt) == course_status(repo, original), original["student_code"]
