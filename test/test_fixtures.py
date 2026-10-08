"""Lớp truy cập dữ liệu trả về đúng tình trạng học tập cho các sinh viên kiểm thử."""
import pandas as pd
import pytest

EXP = pd.read_csv("test/fixtures/students/expected_course_status.csv", keep_default_na=False, dtype=str)
CASES = [tuple(x) for x in EXP[["university_code", "student_code"]].drop_duplicates().values]


@pytest.mark.parametrize("uni,code", CASES)
def test_mon_da_dat_va_mon_dang_no_khop_mong_doi(repo_all, uni, code):
    sv = repo_all.students()
    s = sv[(sv["university_code"] == uni) & (sv["student_code"] == code)].iloc[0]
    e = EXP[(EXP["university_code"] == uni) & (EXP["student_code"] == code)]
    assert set(s["passed_courses"]) == set(e[e["expected_status"] == "passed"]["course_code"])
    assert set(s["outstanding_courses"]) == set(e[e["expected_status"] == "retake"]["course_code"])
    assert set(repo_all.curriculum_courses(s["curriculum_code"])["course_code"]) == set(e["course_code"])
