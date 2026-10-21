"""Hợp đồng cho thuật toán gợi ý `src.recommender.recommend(repo, student, k)`.

`student` là một dòng của repo.students(). Gợi ý dựa trên DỮ LIỆU HỌC TẬP của sinh viên (môn đã
đạt/trượt, điểm, tiến độ, tiên quyết); sở thích tự khai chỉ là tín hiệu phụ. Công thức của từng tiêu chí
ở docs/architecture/ranking.md.

Import thẳng, không `importorskip`: module này đã có trên main, nên nếu nó vỡ thì bộ test này phải đỏ
chứ không được lặng lẽ bỏ qua.
"""
import json
from itertools import combinations
from pathlib import Path

import pandas as pd
import pytest

import src.recommender as rec

EXP = pd.read_csv("test/fixtures/students/expected_course_status.csv", keep_default_na=False, dtype=str)
STATUS = {(r.university_code, r.student_code, r.course_code): r.expected_status for r in EXP.itertuples()}
CASES = [tuple(x) for x in EXP[["university_code", "student_code"]].drop_duplicates().values]


def _run(repo, uni, code, k=5):
    sv = repo.students()
    s = sv[(sv["university_code"] == uni) & (sv["student_code"] == code)].iloc[0]
    return s, [x["course_code"] for x in rec.recommend(repo, s, k=k)["items"]]


@pytest.mark.parametrize("uni,code", CASES)
def test_chi_goi_y_mon_hoc_duoc_trong_khung(repo_all, uni, code):
    _, ds = _run(repo_all, uni, code)
    sai = [(m, STATUS.get((uni, code, m), "không thuộc khung")) for m in ds
           if STATUS.get((uni, code, m)) not in ("eligible", "retake")]
    assert not sai, sai


@pytest.mark.parametrize("uni,code", [c for c in CASES if any(STATUS.get((*c, m)) == "retake"
                                                             for m in EXP["course_code"])])
def test_goi_y_mon_can_hoc_lai(repo_all, uni, code):
    _, ds = _run(repo_all, uni, code)
    can = {m for (u, c, m), st in STATUS.items() if (u, c) == (uni, code) and st == "retake"}
    assert can <= set(ds)


# Hợp đồng mục 7, bất biến "Có ích". Đổi số này là đổi hợp đồng.
PRECISION_AT_5_FLOOR = 0.85


def _recommend_everyone(repo):
    """Gợi ý `k = 20` cho mọi sinh viên, tính một lần cho cả module.

    Năm phần tử đầu của danh sách `k = 20` trùng với danh sách `k = 5`: `pick_items` chọn tham lam từ trên
    xuống và chỉ dừng theo `k`. Nên một lần tính phục vụ được cả bài kiểm khối tự chọn lẫn precision@5."""
    return [(student, rec.recommend(repo, student, k=20)["items"]) for _, student in repo.students().iterrows()]


@pytest.fixture(scope="module")
def recommended(repo):
    return _recommend_everyone(repo)


@pytest.fixture(scope="module")
def recommended_all(repo_all):
    return _recommend_everyone(repo_all)


def _can_fill_exactly(gap, credits):
    """Ghép được đúng `gap` tín chỉ từ `credits`, mỗi môn dùng một lần. Viết độc lập với
    `src/recommender/selection.py` để test không lặp lại chính code nó kiểm."""
    return any(sum(chosen) == gap for size in range(len(credits) + 1) for chosen in combinations(credits, size))


@pytest.mark.parametrize(("dataset", "results"), [("repo", "recommended"), ("repo_all", "recommended_all")])
def test_elective_blocks_stay_exactly_completable_for_every_student(request, dataset, results):
    """Khối `choose_credits` phải chọn ĐÚNG `required_credits` (hợp đồng mục 6.2). Với mọi sinh viên, tín
    chỉ đã đạt cộng tín chỉ được gợi ý trong mỗi khối không vượt `required_credits`, và phần còn thiếu
    vẫn ghép đúng được từ các môn chưa đạt, chưa được gợi ý của khối.

    Kiểm tổng sau cùng chứ không kiểm từng bước chọn. Bản trước kiểm "khối đã đủ thì bỏ" — đúng như code
    đã viết — nên không bắt được việc gợi ý 2 + 2 + 3 tín chỉ cho khối cần 5."""
    repo = request.getfixturevalue(dataset)
    curricula = {}
    errors = []
    for student, items in request.getfixturevalue(results):
        curriculum = student["curriculum_code"]
        if curriculum not in curricula:
            curricula[curriculum] = (repo.curriculum_courses(curriculum).set_index("course_code"),
                                     repo.elective_blocks(curriculum).set_index("block_code")["required_credits"])
        courses, required = curricula[curriculum]
        passed = set(student["passed_courses"])
        picked = {item["course_code"] for item in items}
        for block, need in required.items():
            members = courses[courses["elective_block"] == block]["credits"]
            total = int(members[members.index.isin(passed | picked)].sum())
            rest = [int(c) for code, c in members.items() if code not in passed | picked]
            if total > need or not _can_fill_exactly(int(need) - total, rest):
                errors.append((student["student_code"], block, f"{total}/{need}"))
    assert not errors, f"{len(errors)} lỗi, ví dụ {errors[:5]}"


def test_precision_at_5_meets_the_contract_floor(repo, recommended):
    """Bất biến "Có ích" (hợp đồng mục 7): trung bình trên mọi sinh viên của `data/synthetic`, tỷ lệ môn
    trong năm gợi ý đầu có mặt trong đăng ký dự kiến của học kỳ gợi ý không thấp hơn ngưỡng.

    Đây là mốc chống thụt lùi: đăng ký dự kiến được sinh theo lộ trình chuẩn của khung, nên con số đo mức
    khớp với lộ trình đó chứ không đo hành vi của sinh viên thật."""
    term = repo.setting("target_term_code")
    registrations = pd.read_csv("data/synthetic/course_registrations.csv", dtype=str)
    registrations = registrations[registrations["term_code"] == term]
    expected = registrations.groupby("student_code")["course_code"].apply(set).to_dict()
    precision = [len({item["course_code"] for item in items[:5]} & expected.get(student["student_code"], set())) / 5
                 for student, items in recommended]
    mean = sum(precision) / len(precision)
    assert precision, "không có sinh viên nào để đo"
    assert mean >= PRECISION_AT_5_FLOOR, f"precision@5 = {mean:.4f} < {PRECISION_AT_5_FLOOR}"


def test_goi_y_tu_chon_theo_diem_manh(repo_all):
    """T16 giỏi chủ đề Dữ liệu, T17 giỏi Toán, còn lại như nhau và không khai sở thích.
    Trong các môn tự chọn được gợi ý, tỷ lệ môn thuộc chủ đề mạnh phải cao hơn tỷ lệ đó trong
    tất cả môn tự chọn sinh viên học được.

    Xét cả danh sách (k = 20, trần của mục 6.6) chứ không riêng năm phần tử đầu: hai sinh viên này
    đang ở kỳ 5, mà mọi môn tự chọn của khung đều dự kiến từ kỳ 6 trở đi, nên đầu danh sách luôn
    là môn bắt buộc đúng kỳ. Đúng thứ tự ưu tiên, nhưng không nói gì về chủ đề."""
    for code, manh in [("T16", "du_lieu"), ("T17", "toan")]:
        s, ds = _run(repo_all, "HUS", code, k=20)
        c = repo_all.curriculum_courses(s["curriculum_code"]).set_index("course_code")
        tu_chon = [m for m in c.index if isinstance(c.loc[m, "elective_block"], str)]
        hoc_duoc = [m for m in tu_chon if STATUS.get(("HUS", code, m)) == "eligible"]
        goi_y = [m for m in ds if m in tu_chon]
        manh_hd = sum(c.loc[m, "primary_topic"] == manh for m in hoc_duoc) / len(hoc_duoc)
        manh_gy = sum(c.loc[m, "primary_topic"] == manh for m in goi_y) / len(goi_y) if goi_y else 0
        assert goi_y and manh_gy > manh_hd, (code, goi_y)


def test_hai_sinh_vien_chi_khac_nhom_cong_bang_co_cung_goi_y(repo_all):
    assert _run(repo_all, "HUS", "T02")[1] == _run(repo_all, "HUS", "T08")[1]


def _t03(repo_all):
    return repo_all.student("HUS", "T03")


def test_every_item_score_is_the_sum_of_its_reasons_and_every_reason_has_a_weight(recommended):
    """Bất biến "Lời giải thích khớp điểm" và "không có lý do lạ" (mục 7), trên mọi sinh viên."""
    for student, items in recommended:
        for item in items:
            where = (student["student_code"], item["course_code"])
            assert item["score"] == round(sum(r["contribution"] for r in item["reasons"]), 4), where
            assert {r["code"] for r in item["reasons"]} <= set(rec.DEFAULT_WEIGHTS), where
            assert all(r["contribution"] > 0 for r in item["reasons"]), ("mục 4.4 cấm contribution = 0", where)


def test_the_response_echoes_the_merged_weights_and_counts_every_candidate(repo_all):
    result = rec.recommend(repo_all, _t03(repo_all), k=3, weights={"interest": 0})
    assert list(result) == ["what_if", "weights", "candidate_count", "items", "not_eligible"], "thứ tự khóa theo mục 6.6"
    assert result["what_if"] is False
    assert result["weights"] == {**rec.DEFAULT_WEIGHTS, "interest": 0.0}
    expected = sum(st in ("eligible", "retake") for (u, c, _), st in STATUS.items() if (u, c) == ("HUS", "T03"))
    assert result["candidate_count"] == expected, "đếm cả phần vượt k (mục 6.6, quy định 4)"
    assert len(result["items"]) == 3 < result["candidate_count"]


# Trường chi tiết đi kèm từng trạng thái trong một dòng `course-status` (mục 6.5).
DETAIL_FIELDS = {"passed": "last_attempt", "block_complete": "block", "missing_prerequisite": "missing_prerequisites"}


@pytest.mark.parametrize("uni,code", CASES)
def test_not_eligible_holds_every_other_course_with_the_answer_key_status(repo_all, uni, code):
    """Quy định 7 và 8 của mục 6.6: `not_eligible` là đúng phần còn lại của khung — mọi môn không phải
    `retake` hay `eligible` — mang trạng thái của đáp án viết tay, mỗi dòng cùng dạng một dòng `course-status`."""
    result = rec.recommend(repo_all, repo_all.student(uni, code), k=20)
    expected = {course: status for (u, c, course), status in STATUS.items() if (u, c) == (uni, code)}
    rows = result["not_eligible"]
    assert {row["course_code"]: row["status"] for row in rows} == \
        {course: status for course, status in expected.items() if status not in ("retake", "eligible")}
    assert result["candidate_count"] + len(rows) == len(expected), "hai phần cộng lại là cả khung"
    assert [row["course_code"] for row in rows] == sorted(row["course_code"] for row in rows), "mục 3.3"
    for row in rows:
        assert list(row) == ["course_code", "course_name", "credits", "block_code", "status",
                             DETAIL_FIELDS[row["status"]], "text"], row
        assert row["course_name"] in row["text"], row


@pytest.mark.xfail(strict=True, reason="rules.course_status_details() đọc last_attempt từ database thay vì từ dòng "
                                       "sinh viên nên chưa thấy giả định what-if; chờ tầng luật sửa (#16)")
def test_an_assumed_pass_shows_the_assumed_attempt_in_not_eligible(repo_all):
    """Tiêu chí "Trung thực" của README: giả định đạt MAT2505 với 8,0 thì dòng của môn đó phải nói 8,0, không
    phải điểm 3,0 của lần trượt thật. Khi tầng luật sửa, test này qua và `strict` buộc xóa dấu `xfail`."""
    result = rec.recommend(repo_all, _t03(repo_all), assumptions=[{"course_code": "MAT2505", "status": "passed",
                                                                   "score": 8.0}])
    row = next(row for row in result["not_eligible"] if row["course_code"] == "MAT2505")
    assert row["last_attempt"] == {"term_code": "20252", "attempt_no": 2, "score": 8.0, "letter_grade": None}
    assert row["text"] == "Đã đạt Lập trình cơ bản (điểm 8,0)."


def test_two_identical_calls_give_byte_identical_results(repo_all):
    """Bất biến "Tất định" (mục 7)."""
    assumptions = [{"course_code": "MAT2505", "status": "passed", "score": 6.0}]
    first = rec.recommend(repo_all, _t03(repo_all), k=20, assumptions=assumptions)
    second = rec.recommend(repo_all, _t03(repo_all), k=20, assumptions=assumptions)
    assert json.dumps(first, ensure_ascii=False) == json.dumps(second, ensure_ascii=False)


def test_assuming_a_pass_clears_the_retake_and_unlocks_the_courses_that_need_it(repo_all):
    student = _t03(repo_all)
    groups = repo_all.curriculum_courses(student["curriculum_code"]).set_index("course_code")["prerequisite_groups"]
    before = rec.recommend(repo_all, student, k=20)
    after = rec.recommend(repo_all, student, k=20, assumptions=[{"course_code": "MAT2505", "status": "passed",
                                                                 "score": 6.0}])
    assert after["what_if"] is True
    assert "MAT2505" in {i["course_code"] for i in before["items"]}
    assert "MAT2505" not in {i["course_code"] for i in after["items"]}
    assert after["candidate_count"] > before["candidate_count"]
    assert any(any("MAT2505" in g for g in groups[i["course_code"]]) for i in after["items"])


def test_assuming_a_failure_ranks_the_course_as_a_retake_from_the_previous_term(repo_all):
    """T02 đạt hết. Giả định trượt MAT2502: môn đó thành `retake`, lần học giả định thuộc học kỳ chính ngay
    trước kỳ gợi ý (20252, bỏ qua kỳ hè 20253), là lần học thứ hai."""
    result = rec.recommend(repo_all, repo_all.student("HUS", "T02"), k=20,
                           assumptions=[{"course_code": "MAT2502", "status": "failed", "score": 2.0}])
    item = next(i for i in result["items"] if i["course_code"] == "MAT2502")
    assert item["status"] == "retake"
    reason = next(r for r in item["reasons"] if r["code"] == "outstanding_retake")
    assert reason["data"] == {"term_code": "20252", "score": 2.0, "attempt_no": 2}


def test_assumptions_never_reach_the_database(repo_all):
    before = repo_all.student("HUS", "T03")
    results_before = len(repo_all.course_results())
    rec.recommend(repo_all, before, k=5, assumptions=[{"course_code": "MAT2505", "status": "passed", "score": 9.0}])
    after = repo_all.student("HUS", "T03")
    assert len(repo_all.course_results()) == results_before
    assert after["passed_courses"] == before["passed_courses"]
    assert after["outstanding_courses"] == before["outstanding_courses"] == ["MAT2505"]


def test_a_student_read_at_an_earlier_term_is_ranked_as_of_that_term(repo_all):
    """Mục 3.1: nhìn từ đầu kỳ 20251, T04 vẫn nợ MAT2505 từ kỳ 20242 — lý do phải lấy đúng lần học đó, không
    lấy lần học lại đạt ở chính kỳ 20251."""
    result = rec.recommend(repo_all, repo_all.student("HUS", "T04", "20251"), k=5, term_code="20251")
    item = next(i for i in result["items"] if i["course_code"] == "MAT2505")
    assert item["status"] == "retake"
    reason = next(r for r in item["reasons"] if r["code"] == "outstanding_retake")
    assert reason["data"] == {"term_code": "20242", "score": 3.5, "attempt_no": 1}


@pytest.mark.parametrize(("kwargs", "message"), [
    ({"weights": {"unlocks": -1}}, "unlocks"),
    ({"weights": {"popularity": 1}}, "popularity"),
    ({"assumptions": [{"course_code": "XYZ999", "status": "passed"}]}, r"assumptions\[0\]\.course_code"),
])
def test_invalid_weights_and_assumptions_raise_value_error(repo_all, kwargs, message):
    with pytest.raises(ValueError, match=message):
        rec.recommend(repo_all, _t03(repo_all), **kwargs)


def _contract_response_example(section, marker):
    """Khối JSON ví dụ phản hồi đứng sau `marker` trong mục `section` của hợp đồng. Ví dụ là một phần của
    đặc tả, nên test đọc thẳng từ tài liệu: sửa ví dụ mà không sửa code (hay ngược lại) sẽ làm test đỏ."""
    text = Path("docs/architecture/api-contract.md").read_text(encoding="utf-8")
    after = text[text.index(f"### {section} "):]
    after = after[after.index(marker):]
    start = after.index("```json") + len("```json")
    return json.loads(after[start:after.index("```", start)])


def test_the_recommendation_example_of_the_contract_is_what_t03_really_gets(repo_all):
    example = _contract_response_example("6.6", "Phản hồi, rút gọn còn hai học phần:")
    result = rec.recommend(repo_all, repo_all.student("HUS", "T03"), k=2)
    assert result["items"] == example["items"]
    assert all(row in result["not_eligible"] for row in example["not_eligible"]), "ví dụ rút gọn, nhưng phải có thật"
    assert result["candidate_count"] == example["candidate_count"]
    assert result["weights"] == example["weights"]
    assert result["what_if"] == example["what_if"]
    assert rec.ALGORITHM_VERSION == example["algorithm_version"]
