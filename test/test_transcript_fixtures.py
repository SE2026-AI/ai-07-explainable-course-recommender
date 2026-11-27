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
from src.explain import status_text, violation_text
from src.rules.plan import check_plan, plan_total_credits
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
    courses = repo.curriculum_courses(curriculum_code).set_index("course_code")
    earned = sum(int(courses.loc[c, "credits"]) for c in passed if bool(courses.loc[c, "counts_toward_total"]))
    return {"student_id": None, "university_code": university_code, "curriculum_code": curriculum_code,
            "credits_earned": earned,
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
    to_graduate = max(0, int(curriculum["total_credits"]) - expected["transcript"]["credits_earned"])
    floor = min(request["min_credits"], to_graduate)
    assert ("below_min_credits" in recommended["warnings"]) == (recommended["total_credits"] < floor)


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


def _contract_t03_window():
    """Bảng điểm và khoảng tín chỉ của ví dụ mục 6.11: danh sách gợi ý có HUS1012 (Kỹ năng bổ trợ)."""
    body = _contract_block("6.11", "Body gồm mọi trường")
    return "HUS", "HUS-7480113QTD-2022", {**_t03_body(), **{key: body[key] for key in ("min_credits", "max_credits")}}


def _window_cases():
    return [(path.stem, path) for path in FIXTURES] + [("vi-du-6.11-T03", None)]


@pytest.mark.parametrize("name,path", _window_cases(), ids=[name for name, _ in _window_cases()])
def test_a_recommended_list_passes_the_plan_check_credit_rules(repo_all, name, path):
    """Bất biến "Gợi ý khớp kiểm tra kế hoạch" (mục 7): đưa `items` của mục 6.11 vào mục 6.12, cùng bảng điểm và cùng
    khoảng tín chỉ, thì hai mục ra cùng một tổng, không có `credit_limit_exceeded`, và có `credit_below_minimum` khi
    và chỉ khi mục 6.11 cảnh báo `below_min_credits`. Lỗi số 1 của review 27/11: mục 6.12 từng bỏ tín chỉ của Kỹ năng
    bổ trợ (khối không tính vào tổng tín chỉ tốt nghiệp) mà mục 6.11 thì cộng, nên cùng danh sách ra hai tổng."""
    if path is None:
        university_code, curriculum_code, request = _contract_t03_window()
    else:
        data = _load(path)
        university_code, curriculum_code, request = data["university_code"], data["curriculum_code"], data["request"]
    row = _transcript_row(repo_all, university_code, curriculum_code, request)
    result = rec.recommend(repo_all, row, **_window_kwargs(request))
    codes = [item["course_code"] for item in result["items"]]

    total = result["credit_window"]["total_credits"]
    assert total == plan_total_credits(repo_all.curriculum_courses(curriculum_code), codes), "tổng của mục 6.12"
    violations = {v["code"] for v in check_plan(repo_all, row, codes, **_window_kwargs(request))}
    assert "credit_limit_exceeded" not in violations
    if "credits_to_graduate" in result["credit_window"] and "credit_below_minimum" in violations:
        pytest.xfail("§6.12 chưa hạ mức sàn kỳ cuối như §6.11: FIX-3b, #63")
    below = "below_min_credits" in {warning["code"] for warning in result["warnings"]}
    assert ("credit_below_minimum" in violations) == below
    # Tầng luật cũng ra đúng tổng đó: khoảng khít bằng tổng của mục 6.11 thì không có vi phạm tín chỉ nào.
    tight = {v["code"] for v in check_plan(repo_all, row, codes, min_credits=total, max_credits=total)}
    assert not tight & {"credit_limit_exceeded", "credit_below_minimum"}, tight


def test_the_plan_check_example_of_the_contract_is_t03(repo_all):
    """Mục 6.12: kế hoạch của mục 6.7 với bảng điểm của T03. Vi phạm gắn với môn lấy từ `check_plan()` của tầng
    luật; khoảng tín chỉ chưa có ở tầng luật (RULES-6), nên `credit_below_minimum` được kiểm bằng phép so và câu
    `text` của tầng giải thích. Khi `check_plan()` nhận `min_credits`, `max_credits`, test này phải gọi thẳng nó."""
    body = _contract_block("6.12", "Body gồm mọi trường")
    example = _contract_block("6.12", "Phản hồi:")
    curriculum_code = example["curriculum_code"]
    row = _transcript_row(repo_all, "HUS", curriculum_code, _t03_body())
    courses = repo_all.curriculum_courses(curriculum_code).set_index("course_code")
    names = courses["course_name"].to_dict()

    total = plan_total_credits(courses.reset_index(), body["course_codes"])
    assert (example["min_credits"], example["max_credits"]) == (body["min_credits"], body["max_credits"])
    assert example["total_credits"] == total == 17
    assert example["target_semester"] == _t03_body()["semesters_completed"] + 1
    assert example["max_credits_per_term"] == int(repo_all.curriculum(curriculum_code)["max_credits_per_term"])
    assert body["min_credits"] > total, "ví dụ phải có credit_below_minimum"
    assert body["max_credits"] >= total, "nên không có credit_limit_exceeded"

    expected = [{**v, "text": violation_text(v, courses.loc[v["course_code"]].to_dict(), names)}
                for v in check_plan(repo_all, row, body["course_codes"]) if v["code"] != "credit_limit_exceeded"]
    below = {"code": "credit_below_minimum", "course_code": None,
             "data": {"min_credits": body["min_credits"], "total_credits": total}}
    expected.append({**below, "text": violation_text(below, None, names)})
    # Mục 3.2: trường không áp dụng thì vắng mặt, nên `course_code = None` của tầng luật không có trong ví dụ.
    fields = ("code", "course_code", "text", "data")
    assert example["violations"] == [{k: v[k] for k in fields if v.get(k) is not None} for v in expected]
    assert example["valid"] is False
    assert example["warnings"] == row["warnings"] == []


def _fixture_row(repo, name):
    data = _load(Path(f"test/fixtures/transcripts/{name}.json"))
    return data, _transcript_row(repo, data["university_code"], data["curriculum_code"], data["request"])


def test_a_student_with_fewer_credits_left_than_the_minimum_gets_no_warning(repo):
    """Mục 6.11, quy định 4: `sap-tot-nghiep` còn 7 tín chỉ để tốt nghiệp, gợi ý đúng 7, không cảnh báo."""
    data, row = _fixture_row(repo, "sap-tot-nghiep")
    result = rec.recommend(repo, row, **_window_kwargs(data["request"]))
    assert result["credit_window"] == {
        "min_credits": 10, "max_credits": 20, "total_credits": 7, "credits_to_graduate": 7,
        "text": "Tổng 7 tín chỉ: bạn chỉ còn 7 tín chỉ để tốt nghiệp, nên không cần đủ mức tối thiểu 10 bạn đặt."}
    assert result["warnings"] == []


def test_the_shortfall_warning_blames_the_skipped_courses_when_the_student_skipped_them(repo):
    """Bỏ qua mọi môn trừ ba môn 2 tín chỉ: câu cảnh báo phải chỉ vào danh sách "chưa học kỳ này", không vào mức
    tối đa hay luật khối như bản 1.1.0."""
    data, row = _fixture_row(repo, "nam-nhat")
    window = {"min_credits": 10, "max_credits": 20}
    every = rec.recommend(repo, row, **window)
    keep = {"PHI1002", "HIS1001", "POL1001"}
    skip = [line["course_code"] for line in every["items"] + every["not_selected"] if line["course_code"] not in keep]
    result = rec.recommend(repo, row, skip=skip, **window)
    assert result["credit_window"]["total_credits"] == 6
    [warning] = result["warnings"]
    skipped = [line for line in result["not_selected"] if line["reason"] == "skipped"]
    assert warning["data"] == {"min_credits": 10, "total_credits": 6, "cause": "skipped",
                               "skipped_courses": len(skipped), "skipped_credits": sum(c["credits"] for c in skipped)}
    assert "bạn đã chọn chưa học" in warning["text"]
