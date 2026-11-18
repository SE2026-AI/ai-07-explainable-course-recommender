"""Bảng điểm sinh viên tự nhập (hợp đồng mục 6.10, 6.11): bốn fixture ở `test/fixtures/transcripts/` và hai ví dụ
của hợp đồng.

Mỗi fixture là một bảng điểm chép từ một sinh viên có thật của `data/synthetic`, kèm đáp án: tiến độ mà mục 6.10
phải trả, và danh sách gợi ý mà mục 6.11 phải trả. Đáp án tiến độ đối chiếu được với cơ sở dữ liệu, vì cùng một
sinh viên; riêng `sap-tot-nghiep` cộng thêm giả định đạt các môn đã đăng ký nên không còn bản gốc để so.

Tầng luật chưa có hàm dựng dòng sinh viên từ bảng điểm tự nhập, nên `_transcript_row()` dưới đây dựng tạm theo
đúng quy định của mục 6.10: đạt khi `score >= pass_score`, môn được miễn là đạt và không có điểm. Khi tầng luật
có hàm đó, các test này phải chuyển sang dùng nó.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import src.recommender as rec
from src.explain import status_text
from src.rules.status import course_status_details

FIXTURES = sorted(Path("test/fixtures/transcripts").glob("*.json"))
CONTRACT = Path("docs/architecture/api-contract.md")
SEED = Path("data/seed")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _transcript_row(repo, university_code, curriculum_code, body):
    """Dòng sinh viên cùng dạng `repo.student()`, đủ cho `recommend()`, từ body của mục 6.10."""
    pass_score = float(repo.curriculum(curriculum_code)["pass_score"])
    attempts, scores, passed, outstanding = {}, {}, [], []
    for result in body["results"]:
        code, score = result["course_code"], result.get("score")
        if result.get("exempted"):
            status = "exempted"
        else:
            status = "passed" if score >= pass_score else "failed"
            scores[code] = float(score)
        (outstanding if status == "failed" else passed).append(code)
        attempts[code] = {"semester": result["semester"], "score": None if score is None else float(score),
                          "letter_grade": None, "status": status}
    return {"student_id": None, "university_code": university_code, "curriculum_code": curriculum_code,
            "target_semester": body["semesters_completed"] + 1,
            "passed_courses": sorted(passed), "outstanding_courses": sorted(outstanding),
            "latest_scores": scores, "latest_attempts": attempts, "warnings": []}


def _window_kwargs(request):
    return {"min_credits": request["min_credits"], "max_credits": request["max_credits"]}


# ---------------- Hình dạng: không cần database ----------------

def test_there_is_one_fixture_for_each_case_of_the_issue():
    assert [path.stem for path in FIXTURES] == ["khoi-tu-chon-gan-day", "nam-nhat", "no-nhieu-mon", "sap-tot-nghiep"]


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_every_fixture_is_a_valid_body_of_the_contract(path):
    """Mọi quy định của bảng trường ở mục 6.10 và 6.11, đối chiếu với CSV của `data/seed`."""
    data = _load(path)
    request = data["request"]
    curricula = pd.read_csv(SEED / "curricula.csv", dtype=str).set_index("code")
    schemes = pd.read_csv(SEED / "grading_schemes.csv", dtype=str).set_index("code")
    members = pd.read_csv(SEED / "curriculum_courses.csv", dtype=str)
    curriculum = curricula.loc[data["curriculum_code"]]
    codes = set(members[members["curriculum_code"] == data["curriculum_code"]]["course_code"])
    max_score = float(schemes.loc[curriculum["grading_scheme_code"], "max_score"])

    assert set(data) == {"description", "source", "university_code", "curriculum_code", "request", "expected"}
    assert curriculum["university_code"] == data["university_code"]
    done = request["semesters_completed"]
    assert isinstance(done, int) and 0 <= done <= 12
    seen = [result["course_code"] for result in request["results"]]
    assert len(seen) == len(set(seen)), "mỗi mã nhiều nhất một lần"
    assert set(seen) <= codes, set(seen) - codes
    for result in request["results"]:
        assert isinstance(result["semester"], int) and 1 <= result["semester"] <= done, result
        assert ("score" in result) != ("exempted" in result), result
        if "score" in result:
            assert 0 <= result["score"] <= max_score, result
        else:
            assert result["exempted"] is True, result
    assert 10 <= request["min_credits"] <= request["max_credits"] <= int(curriculum["max_credits_per_term"])

    expected = data["expected"]
    assert expected["transcript"]["target_semester"] == done + 1
    recommended = expected["recommendations"]
    assert set(recommended["items"]) <= codes and set(recommended["not_selected"]) <= codes
    assert not set(recommended["items"]) & set(recommended["not_selected"])
    assert set(recommended["not_selected"].values()) <= {"skipped", "block_full", "credit_budget"}
    assert recommended["total_credits"] <= request["max_credits"]
    assert ("below_min_credits" in recommended["warnings"]) == (recommended["total_credits"] < request["min_credits"])


# ---------------- Đối chiếu với cơ sở dữ liệu ----------------

@pytest.mark.parametrize("path", [path for path in FIXTURES if "assumed_passed" not in _load(path)["source"]],
                         ids=lambda path: path.stem)
def test_a_fixture_copies_its_source_student_and_the_expected_progress_is_the_database_one(repo, path):
    """Bất biến "Bảng điểm tự nhập trùng cơ sở dữ liệu" (mục 7), đọc theo chiều ngược: bảng điểm chép đúng lần
    học gần nhất của từng môn, nên tiến độ trong đáp án phải trùng tiến độ mà cơ sở dữ liệu tính cho sinh viên đó."""
    data = _load(path)
    source = data["source"]
    student = repo.student(data["university_code"], source["student_code"], source["term"])
    assert student["curriculum_code"] == data["curriculum_code"]
    copied = {result["course_code"]: result.get("score") for result in data["request"]["results"]}
    assert copied == {code: attempt["score"] for code, attempt in student["latest_attempts"].items()}
    progress = data["expected"]["transcript"]
    assert progress["credits_earned"] == int(student["credits_earned"])
    assert progress["credits_outstanding"] == int(student["credits_outstanding"])
    assert progress["gpa"] == (None if pd.isna(student["gpa"]) else round(float(student["gpa"]), 2))
    assert progress["outstanding_courses"] == sorted(student["outstanding_courses"])


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_the_recommendation_of_every_fixture_is_its_expected_one(repo, path):
    data = _load(path)
    request = data["request"]
    row = _transcript_row(repo, data["university_code"], data["curriculum_code"], request)
    result = rec.recommend(repo, row, **_window_kwargs(request))
    expected = data["expected"]["recommendations"]
    assert [item["course_code"] for item in result["items"]] == expected["items"]
    assert result["credit_window"]["total_credits"] == expected["total_credits"]
    assert {row["course_code"]: row["reason"] for row in result["not_selected"]} == expected["not_selected"]
    assert [warning["code"] for warning in result["warnings"]] == expected["warnings"]
    assert result["target_semester"] == data["expected"]["transcript"]["target_semester"]
    assert set(row["outstanding_courses"]) == set(data["expected"]["transcript"]["outstanding_courses"])


# ---------------- Ví dụ của hợp đồng ----------------

def _contract_block(section, marker, nth=0):
    """Khối JSON thứ `nth` sau `marker` trong mục `section`: ví dụ là đặc tả, nên test đọc thẳng từ tài liệu."""
    text = CONTRACT.read_text(encoding="utf-8")
    after = text[text.index(f"### {section} "):]
    after = after[after.index(marker):]
    for _ in range(nth + 1):
        start = after.index("```json") + len("```json")
        block, after = after[start:after.index("```", start)], after[after.index("```", start) + 3:]
    return json.loads(block)


def _t03_body():
    return _contract_block("6.10", "Body:")


def test_the_transcript_example_of_the_contract_is_t03(repo_all):
    """Body của mục 6.10 là lần học gần nhất của mọi môn của T03, kỳ nhập học 20251 là kỳ 1."""
    body = _t03_body()
    student = repo_all.student("HUS", "T03")
    terms = sorted({attempt["term_code"] for attempt in student["latest_attempts"].values()})
    assert body["semesters_completed"] == len(terms) == 2
    assert {r["course_code"]: (r["semester"], r["score"]) for r in body["results"]} == \
        {code: (terms.index(a["term_code"]) + 1, a["score"]) for code, a in student["latest_attempts"].items()}


def test_the_transcript_response_example_matches_t03_in_the_database(repo_all):
    """Mục 6.10: bảng điểm của T03 cho đúng tiến độ của mục 6.4 và đúng trạng thái của mục 6.5."""
    example = _contract_block("6.10", "Phản hồi, `courses` rút gọn còn hai học phần:")
    student = repo_all.student("HUS", "T03")
    curriculum = repo_all.curriculum(example["curriculum_code"])
    for field in ("credits_earned", "credits_outstanding"):
        assert example[field] == int(student[field]), field
    for field in ("total_credits", "max_credits_per_term"):
        assert example[field] == int(curriculum[field]), field
    assert example["gpa"] == round(float(student["gpa"]), 2)
    assert example["outstanding_courses"] == sorted(student["outstanding_courses"])
    assert example["target_semester"] == example["semesters_completed"] + 1 == 3

    body = _t03_body()
    row = _transcript_row(repo_all, "HUS", example["curriculum_code"], body)
    details = course_status_details(repo_all, row)
    statuses = pd.Series({code: detail["status"] for code, detail in details.items()})
    assert example["summary"] == statuses.value_counts().to_dict()

    def without_attempt(rows):
        """`last_attempt` của bảng điểm tự nhập ghi `semester` thay cho `term_code`, nên so phần còn lại."""
        return {code: {k: v for k, v in detail.items() if k != "last_attempt"} for code, detail in rows.items()}

    assert without_attempt(details) == without_attempt(course_status_details(repo_all, student))

    courses = repo_all.curriculum_courses(example["curriculum_code"]).set_index("course_code", drop=False)
    names = courses["course_name"].to_dict()
    for line in example["courses"]:
        code = line["course_code"]
        assert line["status"] == details[code]["status"], code
        semester = next(r["semester"] for r in body["results"] if r["course_code"] == code)
        assert line["last_attempt"]["semester"] == semester
        detail = {"status": line["status"], "last_attempt": line["last_attempt"]}
        assert line["text"] == status_text(courses.loc[code].to_dict(), detail, names), code


def test_the_credit_window_example_of_the_contract_is_what_t03_really_gets(repo_all):
    """Mục 6.11: phản hồi rút gọn có thật, và đoạn "Đầy đủ" ngay sau nó kể đúng cả danh sách."""
    body = _contract_block("6.11", "Body gồm mọi trường")
    example = _contract_block("6.11", "Phản hồi, `items` rút gọn")
    row = _transcript_row(repo_all, "HUS", example["curriculum_code"], _t03_body())
    result = rec.recommend(repo_all, row, weights=body["weights"], skip=body["skip"], include=body["include"],
                           **_window_kwargs(body))

    assert list(result) == ["what_if", "weights", "target_semester", "credit_window", "candidate_count", "items",
                            "not_selected", "not_eligible", "warnings"], "thứ tự khóa theo mục 6.11"
    for field in ("what_if", "weights", "target_semester", "credit_window", "candidate_count", "warnings"):
        assert result[field] == example[field], field
    assert rec.ALGORITHM_VERSION == example["algorithm_version"]
    assert [result["items"][0], result["items"][-1]] == example["items"]
    assert all(line in result["not_selected"] for line in example["not_selected"]), "rút gọn, nhưng phải có thật"
    assert all(line in result["not_eligible"] for line in example["not_eligible"]), "rút gọn, nhưng phải có thật"

    assert [item["course_code"] for item in result["items"]] == \
        ["MAT2505", "MAT2323", "HIS1056", "PHI1002", "HUS1012", "HIS1001", "MAT2407"]
    assert [(line["course_code"], line["reason"]) for line in result["not_selected"]] == [
        ("HUS1024", "block_full"), ("MAT2503", "skipped"), ("HUS1021", "block_full"), ("HUS1023", "block_full"),
        ("MAT2403", "credit_budget"), ("MAT1205E", "credit_budget"), ("POL1001", "credit_budget"),
        ("THL1057", "credit_budget"), ("MAT4080", "credit_budget")]

    without = rec.recommend(repo_all, row, skip=body["skip"], **_window_kwargs(body))
    assert "MAT2407" not in {item["course_code"] for item in without["items"]}
    assert "MAT2403" in {item["course_code"] for item in without["items"]}, "chỗ đó thuộc về MAT2403 khi không include"
