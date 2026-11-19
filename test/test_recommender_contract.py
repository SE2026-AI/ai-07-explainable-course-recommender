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


T03_TOP_5 = ["MAT2505", "MAT2323", "HIS1056", "MAT2503", "PHI1002"]


def test_skipping_a_course_hands_its_place_to_the_next_one(repo_all):
    """T03 chưa muốn học Xác suất - Thống kê kỳ này: môn xếp thứ 6 lên thế chỗ, trạng thái học phần không đổi
    (mục 6.6, quy định 9)."""
    before = rec.recommend(repo_all, _t03(repo_all), k=5)
    after = rec.recommend(repo_all, _t03(repo_all), k=5, skip=["MAT2323"])
    assert [i["course_code"] for i in before["items"]] == T03_TOP_5
    assert [i["course_code"] for i in after["items"]] == ["MAT2505", "HIS1056", "MAT2503", "PHI1002", "HUS1012"]
    assert [i["rank"] for i in after["items"]] == [1, 2, 3, 4, 5]
    assert after["what_if"] is True
    assert after["candidate_count"] == before["candidate_count"]
    assert after["not_eligible"] == before["not_eligible"]


def test_swapping_a_course_brings_in_the_replacement_at_its_own_score(repo_all):
    """Đổi Xác suất - Thống kê lấy Tối ưu hóa (vốn xếp thứ 10): Tối ưu hóa có mặt, đứng theo điểm của chính nó."""
    result = rec.recommend(repo_all, _t03(repo_all), k=5,
                           swap=[{"course_code": "MAT2323", "replacement": "MAT2407"}])
    assert [i["course_code"] for i in result["items"]] == ["MAT2505", "HIS1056", "MAT2503", "PHI1002", "MAT2407"]
    scores = [i["score"] for i in result["items"]]
    assert scores == sorted(scores, reverse=True), "mục 3.3"


def test_a_swap_inside_an_elective_block_keeps_the_block_exact(repo_all):
    """T03 đã đạt HUS1022 (2 tín chỉ) của khối II cần 5. Đổi HIS1056 lấy HUS1024 (cùng 3 tín chỉ) thì được;
    đổi lấy HUS1023 (2 tín chỉ) thì khối còn thiếu 1 mà không môn nào đủ nhỏ, nên bị từ chối."""
    result = rec.recommend(repo_all, _t03(repo_all), k=5,
                           swap=[{"course_code": "HIS1056", "replacement": "HUS1024"}])
    assert "HUS1024" in {i["course_code"] for i in result["items"]}
    with pytest.raises(ValueError, match=r"^swap\[0\]\.replacement: HUS1023"):
        rec.recommend(repo_all, _t03(repo_all), swap=[{"course_code": "HIS1056", "replacement": "HUS1023"}])


def test_the_request_example_of_the_contract_is_accepted(repo_all):
    body = json.loads(_contract_block("6.6", "Body `POST`:"))
    result = rec.recommend(repo_all, _t03(repo_all), k=body["limit"], weights=body["weights"],
                           assumptions=body["assumptions"], skip=body["skip"], swap=body["swap"])
    codes = [i["course_code"] for i in result["items"]]
    assert body["skip"][0] not in codes and body["swap"][0]["course_code"] not in codes
    assert body["swap"][0]["replacement"] in codes


@pytest.mark.parametrize(("kwargs", "message"), [
    ({"weights": {"unlocks": -1}}, "unlocks"),
    ({"weights": {"popularity": 1}}, "popularity"),
    ({"assumptions": [{"course_code": "XYZ999", "status": "passed"}]}, r"assumptions\[0\]\.course_code"),
    ({"skip": ["HUS1022"]}, r"skip\[0\]"),
    ({"swap": [{"course_code": "MAT2323", "replacement": "MAT1203"}]}, r"swap\[0\]\.replacement"),
])
def test_invalid_weights_and_assumptions_raise_value_error(repo_all, kwargs, message):
    with pytest.raises(ValueError, match=message):
        rec.recommend(repo_all, _t03(repo_all), **kwargs)


def _contract_block(section, marker):
    """Khối JSON ví dụ đứng sau `marker` trong mục `section` của hợp đồng. Ví dụ là một phần của đặc tả, nên
    test đọc thẳng từ tài liệu: sửa ví dụ mà không sửa code (hay ngược lại) sẽ làm test đỏ."""
    text = Path("docs/architecture/api-contract.md").read_text(encoding="utf-8")
    after = text[text.index(f"### {section} "):]
    after = after[after.index(marker):]
    start = after.index("```json") + len("```json")
    return after[start:after.index("```", start)]


def _contract_response_example(section, marker):
    return json.loads(_contract_block(section, marker))


def test_the_recommendation_example_of_the_contract_is_what_t03_really_gets(repo_all):
    example = _contract_response_example("6.6", "Phản hồi, rút gọn còn hai học phần:")
    result = rec.recommend(repo_all, repo_all.student("HUS", "T03"), k=2)
    assert result["items"] == example["items"]
    assert all(row in result["not_eligible"] for row in example["not_eligible"]), "ví dụ rút gọn, nhưng phải có thật"
    assert result["candidate_count"] == example["candidate_count"]
    assert result["weights"] == example["weights"]
    assert result["what_if"] == example["what_if"]
    assert rec.ALGORITHM_VERSION == example["algorithm_version"]


# ---------------- Gợi ý theo khoảng tín chỉ (mục 6.11) ----------------

WINDOW_KEYS = ["what_if", "weights", "target_semester", "credit_window", "candidate_count", "items", "not_selected",
               "not_eligible", "warnings"]


def _window(repo, student, low=10, high=20):
    """Khoảng tín chỉ hợp lệ với mọi khung: trần không vượt `max_credits_per_term` (khung DEMO chỉ cho 12)."""
    cap = int(repo.curriculum(student["curriculum_code"])["max_credits_per_term"])
    return low, min(high, cap)


@pytest.fixture(scope="module")
def windowed_all(repo_all):
    """Gợi ý trong khoảng 10–20 tín chỉ cho mọi sinh viên của `repo_all`, tính một lần cho cả module."""
    results = []
    for _, student in repo_all.students().iterrows():
        low, high = _window(repo_all, student)
        results.append((student, (low, high), rec.recommend(repo_all, student, min_credits=low, max_credits=high)))
    return results


@pytest.fixture(scope="module")
def curriculum_of(repo_all):
    """Mã khung → `(học phần theo mã, tín chỉ phải chọn của từng khối tự chọn)`, đọc mỗi khung một lần."""
    cache = {}

    def read(code):
        if code not in cache:
            cache[code] = (repo_all.curriculum_courses(code).set_index("course_code"),
                           repo_all.elective_blocks(code).set_index("block_code")["required_credits"])
        return cache[code]
    return read


def test_credit_window_invariants_hold_for_every_student(windowed_all, curriculum_of):
    """Bất biến "Khoảng tín chỉ" và "Không môn học được nào bị bỏ lặng lẽ" (mục 7), quy định 3–6 của mục 6.11."""
    errors = []
    for student, (low, high), result in windowed_all:
        who = (student["university_code"], student["student_code"])
        items, left_out = result["items"], result["not_selected"]
        total = sum(item["credits"] for item in items)
        window = result["credit_window"]
        if list(result) != WINDOW_KEYS:
            errors.append((who, "thứ tự khóa", list(result)))
        if (window["min_credits"], window["max_credits"], window["total_credits"]) != (low, high, total):
            errors.append((who, "credit_window", window))
        if total > high:
            errors.append((who, "vượt max_credits", total))
        if ("below_min_credits" in {w["code"] for w in result["warnings"]}) != (total < low):
            errors.append((who, "below_min_credits", total))
        codes = [row["course_code"] for row in items + left_out]
        not_eligible = {row["course_code"] for row in result["not_eligible"]}
        every = set(curriculum_of(student["curriculum_code"])[0].index)
        if len(codes) != len(set(codes)) or set(codes) != every - not_eligible \
                or result["candidate_count"] != len(codes):
            errors.append((who, "items + not_selected phải là đúng mọi môn học được, mỗi môn một lần", codes))
        if [item["rank"] for item in items] != list(range(1, len(items) + 1)):
            errors.append((who, "rank", [item["rank"] for item in items]))
        for line in left_out:
            data = line["data"]
            if line["reason"] == "credit_budget" and not (data["total_credits"] == total
                                                          and total + data["credits"] > high):
                errors.append((who, line["course_code"], "credit_budget mà vẫn vừa", data))
            if line["reason"] == "skipped":
                errors.append((who, line["course_code"], "không gửi skip"))
    assert not errors, f"{len(errors)} lỗi, ví dụ {errors[:5]}"


def test_elective_blocks_stay_exactly_completable_within_a_credit_window(windowed_all, curriculum_of):
    """Cùng bất biến "Khối tự chọn hoàn thành đúng" như khi chọn theo `k`: đổi cách dừng không được đổi luật khối."""
    errors = []
    for student, _, result in windowed_all:
        courses, required = curriculum_of(student["curriculum_code"])
        done = set(student["passed_courses"]) | {item["course_code"] for item in result["items"]}
        for block, need in required.items():
            members = courses[courses["elective_block"] == block]["credits"]
            total = int(members[members.index.isin(done)].sum())
            rest = [int(c) for code, c in members.items() if code not in done]
            if total > need or not _can_fill_exactly(int(need) - total, rest):
                errors.append((student["student_code"], block, f"{total}/{need}"))
        for line in result["not_selected"]:
            if line["reason"] == "block_full":
                block = line["data"]["block_code"]
                members = courses[courses["elective_block"] == block]["credits"]
                if line["data"]["taken_credits"] != int(members[members.index.isin(done)].sum()):
                    errors.append((student["student_code"], line["course_code"], "taken_credits", line["data"]))
    assert not errors, f"{len(errors)} lỗi, ví dụ {errors[:5]}"


def test_a_credit_window_without_choices_is_not_a_what_if_and_keeps_the_ranking_of_k(repo_all):
    """Cùng sinh viên, cùng trọng số: hai cách chọn xếp hạng như nhau, chỉ khác chỗ dừng."""
    by_k = rec.recommend(repo_all, _t03(repo_all), k=20)
    by_window = rec.recommend(repo_all, _t03(repo_all), min_credits=10, max_credits=40)
    assert by_window["what_if"] is False
    assert by_window["target_semester"] == 3
    ranked = [item["course_code"] for item in by_window["items"]]
    assert ranked == [code for code in (item["course_code"] for item in by_k["items"]) if code in ranked]
    assert by_window["not_eligible"] == by_k["not_eligible"]
    assert by_window["candidate_count"] == by_k["candidate_count"]


def test_skip_and_include_inside_a_credit_window(repo_all):
    """Môn `skip` sang `not_selected` với lý do `skipped`; môn `include` luôn có mặt, đứng theo điểm của nó."""
    result = rec.recommend(repo_all, _t03(repo_all), min_credits=15, max_credits=20, skip=["MAT2323"],
                           include=["MAT2407"])
    codes = [item["course_code"] for item in result["items"]]
    assert "MAT2323" not in codes and "MAT2407" in codes
    skipped = next(line for line in result["not_selected"] if line["course_code"] == "MAT2323")
    assert skipped["reason"] == "skipped" and skipped["data"] == {}
    assert skipped["text"] == "Bạn chọn chưa học Xác suất - Thống kê ở kỳ này."
    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True), "mục 3.3"
    assert result["what_if"] is True


def test_the_defaults_of_the_credit_window(repo_all):
    """Gửi một đầu thì đầu kia lấy mặc định: tối thiểu 10, tối đa min(max(20, min_credits), trần của khung)."""
    assert rec.recommend(repo_all, _t03(repo_all), max_credits=30)["credit_window"]["min_credits"] == 10
    assert rec.recommend(repo_all, _t03(repo_all), min_credits=12)["credit_window"]["max_credits"] == 20
    assert rec.recommend(repo_all, _t03(repo_all), min_credits=25)["credit_window"]["max_credits"] == 25


@pytest.mark.parametrize(("kwargs", "message"), [
    ({"min_credits": 9}, r"^min_credits: phải từ 10"),
    ({"max_credits": 41}, r"^max_credits: không được vượt 40"),
    ({"min_credits": 21, "max_credits": 20}, r"^min_credits: phải nhỏ hơn hoặc bằng max_credits"),
    ({"min_credits": 12.5}, r"^min_credits: phải là số nguyên"),
    ({"max_credits": True}, r"^max_credits: phải là số nguyên"),
    ({"include": ["MAT2407"]}, r"^include: chỉ dùng cùng min_credits và max_credits"),
    ({"min_credits": 10, "swap": [{"course_code": "MAT2323", "replacement": "MAT2407"}]}, r"^swap: không dùng"),
    ({"min_credits": 10, "include": ["MAT2502"]}, r"^include\[0\]: "),
    ({"min_credits": 10, "skip": ["MAT2407"], "include": ["MAT2407"]}, r"^include\[0\]: .*skip hoặc include"),
    # T03 đã có 2/5 tín chỉ của khối II: thêm HUS1023 (2) thì còn thiếu 1, không môn nào đủ nhỏ.
    ({"min_credits": 10, "include": ["HUS1023"]}, r"^include\[0\]: HUS1023 làm khối tự chọn II"),
    ({"min_credits": 10, "max_credits": 10, "include": ["MAT2505", "MAT2323", "HIS1056", "PHI1002"]},
     r"^include\[3\]: các môn muốn học cộng lại vượt max_credits = 10"),
])
def test_an_invalid_credit_window_or_choice_names_the_field_that_is_wrong(repo_all, kwargs, message):
    with pytest.raises(ValueError, match=message):
        rec.recommend(repo_all, _t03(repo_all), **kwargs)


def test_the_cap_of_the_credit_window_is_the_one_of_the_curriculum(repo_all):
    """Khung DEMO cho tối đa 12 tín chỉ một kỳ, không phải 40 như HUS."""
    students = repo_all.students()
    demo = students[students["university_code"] == "DEMO"].iloc[0]
    assert rec.recommend(repo_all, demo, max_credits=12)["credit_window"]["max_credits"] == 12
    with pytest.raises(ValueError, match=r"^max_credits: không được vượt 12"):
        rec.recommend(repo_all, demo, max_credits=13)


def test_the_default_maximum_never_exceeds_the_cap_of_the_curriculum(repo_all):
    """Mặc định 20 cao hơn trần 12 của DEMO: chỉ gửi `min_credits` thì tối đa là trần, không phải lỗi ở
    `max_credits`, trường người gọi không gửi. `min_credits` vượt trần thì lỗi ở chính `min_credits`."""
    students = repo_all.students()
    demo = students[students["university_code"] == "DEMO"].iloc[0]
    window = rec.recommend(repo_all, demo, min_credits=10)["credit_window"]
    assert (window["min_credits"], window["max_credits"]) == (10, 12)
    assert rec.recommend(repo_all, demo, min_credits=12)["credit_window"]["max_credits"] == 12
    with pytest.raises(ValueError, match=r"^min_credits: không được vượt 12"):
        rec.recommend(repo_all, demo, min_credits=13)
    with pytest.raises(ValueError, match=r"^min_credits: không được vượt 40"):
        rec.recommend(repo_all, _t03(repo_all), min_credits=41)


def test_a_row_that_carries_its_target_semester_is_ranked_at_that_semester(repo_all):
    """Dòng dựng từ bảng điểm tự nhập mang sẵn `target_semester` (mục 6.10); không tính lại từ năm học."""
    student = _t03(repo_all).copy()
    student["target_semester"] = 5
    result = rec.recommend(repo_all, student, min_credits=10, max_credits=20)
    assert result["target_semester"] == 5
    schedules = [r["data"]["target_semester"] for item in result["items"] for r in item["reasons"]
                 if r["code"] in ("on_time", "overdue")]
    assert schedules and set(schedules) == {5}


def test_a_row_without_a_student_id_gets_no_interest_reason(repo_all):
    """Sinh viên tự nhập bảng điểm chưa khai sở thích (mục 6.11, quy định 10). Không được rơi vào nhánh đọc sở
    thích theo `student_id = None`, vì truy vấn đó trả sở thích của MỌI sinh viên."""
    student = repo_all.student("HUS", "T02")
    with_id = rec.recommend(repo_all, student, k=20)
    assert any(r["code"] == "interest" for item in with_id["items"] for r in item["reasons"]), "T02 có khai sở thích"
    anonymous = student.copy()
    anonymous["student_id"] = None
    result = rec.recommend(repo_all, anonymous, k=20)
    assert not any(r["code"] == "interest" for item in result["items"] for r in item["reasons"])


def test_two_identical_credit_window_calls_give_byte_identical_results(repo_all):
    """Bất biến "Tất định" (mục 7), với khoảng tín chỉ."""
    kwargs = {"min_credits": 15, "max_credits": 20, "skip": ["MAT2503"], "include": ["MAT2407"]}
    first = rec.recommend(repo_all, _t03(repo_all), **kwargs)
    second = rec.recommend(repo_all, _t03(repo_all), **kwargs)
    assert json.dumps(first, ensure_ascii=False) == json.dumps(second, ensure_ascii=False)
