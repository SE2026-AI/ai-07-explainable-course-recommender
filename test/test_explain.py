"""Câu chữ của tầng giải thích: khớp từng chữ với ví dụ của hợp đồng, giữ đúng VÀ/HOẶC, không lộ giá trị rỗng.

Không cần database: tên học phần lấy nguyên từ ví dụ ở mục 6.5 và 6.7 của `api-contract.md`. Riêng test cuối
chạy trên sinh viên kiểm thử thật nên cần PostgreSQL (fixture `repo_all`).
"""
import pandas as pd
import pytest

from src.explain import (
    NOT_SELECTED_REASONS,
    STATUSES,
    VIOLATIONS,
    WARNINGS,
    credit_window_text,
    format_decimal,
    not_selected_text,
    prerequisite_phrase,
    status_text,
    violation_text,
    warning_text,
)
from src.rules.status import course_status_details

NAMES = {"MAT2323": "Xác suất - Thống kê", "MAT2502": "Giải tích 2", "MAT3507": "Cơ sở dữ liệu",
         "MAT2505": "Lập trình cơ bản", "CS101": "Nhập môn lập trình", "HUS1011": "Tin học cơ sở"}


def _course(name, groups=None):
    return {"course_name": name, "prerequisite_groups": groups or []}


@pytest.mark.parametrize(("course", "detail", "expected"), [
    (_course("Lập trình cơ bản", [["HUS1011"]]),
     {"status": "retake", "last_attempt": {"term_code": "20252", "attempt_no": 1, "score": 3.0, "letter_grade": "F"}},
     "Cần học lại Lập trình cơ bản: bạn chưa đạt môn này ở học kỳ 20252 (điểm 3,0)."),
    (_course("Lập trình cơ bản", [["HUS1011"]]),
     {"status": "retake", "last_attempt": {"semester": 2, "score": 3.0, "letter_grade": "F"}},
     "Cần học lại Lập trình cơ bản: bạn chưa đạt môn này ở kỳ 2 (điểm 3,0)."),
    (_course("Học máy", [["MAT2323"]]),
     {"status": "missing_prerequisite", "missing_prerequisites": [["MAT2323"]]},
     "Chưa học được Học máy: cần hoàn thành Xác suất - Thống kê (MAT2323) trước."),
    (_course("Tiếng Nga B1"),
     {"status": "block_complete",
      "block": {"block_code": "I.2", "block_name": "Ngoại ngữ B1", "required_credits": 5, "earned_credits": 5}},
     "Không cần học Tiếng Nga B1: khối Ngoại ngữ B1 đã đủ 5/5 tín chỉ."),
    (_course("Xác suất - Thống kê", [["MAT2502"]]),
     {"status": "eligible"},
     "Học được Xác suất - Thống kê: đã đủ điều kiện tiên quyết."),
    (_course("Triết học Mác - Lênin"),
     {"status": "passed", "last_attempt": {"term_code": "20251", "attempt_no": 1, "score": 7.5, "letter_grade": "B"}},
     "Đã đạt Triết học Mác - Lênin (điểm 7,5)."),
])
def test_status_texts_match_the_contract_examples_word_for_word(course, detail, expected):
    assert status_text(course, detail, NAMES) == expected


def test_the_plan_check_violation_matches_the_contract_example_word_for_word():
    violation = {"code": "missing_prerequisite", "course_code": "MAT3533",
                 "data": {"missing_prerequisites": [["MAT2323"]]}}
    assert violation_text(violation, _course("Học máy"), NAMES) == \
        "Học máy chưa học được: cần hoàn thành Xác suất - Thống kê (MAT2323) trước."


def test_separate_groups_are_joined_with_and():
    assert prerequisite_phrase([["MAT3507"], ["MAT2323"]], NAMES) == \
        "Cơ sở dữ liệu (MAT3507) và Xác suất - Thống kê (MAT2323)"
    assert prerequisite_phrase([["MAT2502"], ["MAT3507"], ["MAT2323"]], NAMES) == \
        "Giải tích 2 (MAT2502), Cơ sở dữ liệu (MAT3507) và Xác suất - Thống kê (MAT2323)"


def test_codes_inside_one_group_are_joined_with_or_and_never_flattened():
    """Mục 4.2: làm phẳng `[["CS101", "MAT2505"]]` thành "A và B" là biến HOẶC thành VÀ."""
    phrase = prerequisite_phrase([["CS101", "MAT2505"]], NAMES)
    assert phrase == "một trong hai môn Nhập môn lập trình (CS101) hoặc Lập trình cơ bản (MAT2505)"
    assert " và " not in phrase


def test_a_mixed_condition_cannot_be_misread():
    """Cần MAT2323 VÀ (CS101 HOẶC MAT2505): câu phải nói "một trong", không được thành "A và B hoặc C"."""
    assert prerequisite_phrase([["MAT2323"], ["CS101", "MAT2505"]], NAMES) == (
        "Xác suất - Thống kê (MAT2323) và một trong hai môn Nhập môn lập trình (CS101) hoặc Lập trình cơ bản (MAT2505)")
    assert prerequisite_phrase([["MAT2502", "MAT3507", "MAT2323"]], NAMES).startswith("một trong các môn ")


def test_a_code_without_a_known_name_falls_back_to_the_code_alone():
    assert prerequisite_phrase([["XYZ999"]], NAMES) == "XYZ999"


@pytest.mark.parametrize("groups", [[], [[]], [["MAT2323"], []]])
def test_empty_prerequisite_groups_are_rejected_rather_than_rendered(groups):
    with pytest.raises(ValueError):
        prerequisite_phrase(groups, NAMES)


def test_an_exempted_course_says_so_instead_of_inventing_a_score():
    detail = {"status": "passed", "last_attempt": {"term_code": "20251", "attempt_no": 1,
                                                   "score": None, "letter_grade": None}}
    assert status_text(_course("Tiếng Anh B1"), detail, NAMES) == "Đã đạt Tiếng Anh B1 (được miễn)."
    detail["last_attempt"]["score"] = float("nan")
    assert status_text(_course("Tiếng Anh B1"), detail, NAMES) == "Đã đạt Tiếng Anh B1 (được miễn)."


def test_an_eligible_course_without_prerequisites_does_not_claim_to_have_met_them():
    assert status_text(_course("Tin học cơ sở"), {"status": "eligible"}, NAMES) == \
        "Học được Tin học cơ sở: môn này không có điều kiện tiên quyết."


def test_a_block_name_that_already_says_khoi_is_not_doubled():
    detail = {"status": "block_complete", "block": {"block_code": "II", "block_name": "Khối kiến thức theo lĩnh vực",
                                                    "required_credits": 5, "earned_credits": 5}}
    text = status_text(_course("Cơ sở văn hóa Việt Nam"), detail, NAMES)
    assert text == "Không cần học Cơ sở văn hóa Việt Nam: khối kiến thức theo lĩnh vực đã đủ 5/5 tín chỉ."


SAMPLE_DETAILS = {
    "passed": {"status": "passed", "last_attempt": {"term_code": "20251", "attempt_no": 2, "score": 6.0}},
    "block_complete": {"status": "block_complete",
                       "block": {"block_name": "Tự chọn", "required_credits": 6, "earned_credits": 6}},
    "missing_prerequisite": {"status": "missing_prerequisite", "missing_prerequisites": [["MAT2323"], ["CS101", "MAT2505"]]},
    "retake": {"status": "retake", "last_attempt": {"term_code": "20252", "attempt_no": 1, "score": None}},
    "eligible": {"status": "eligible"},
}
# `data` đúng dạng `check_plan()` của tầng luật trả về (`src/rules/plan.py`).
SAMPLE_VIOLATIONS = {
    "credit_limit_exceeded": {"code": "credit_limit_exceeded", "course_code": "HIS1056",
                              "data": {"max_credits_per_term": 40, "total_credits": 43}},
    "credit_below_minimum": {"code": "credit_below_minimum", "course_code": None,
                             "data": {"min_credits": 15, "total_credits": 11}},
    "missing_prerequisite": {"code": "missing_prerequisite", "course_code": "MAT3533",
                             "data": {"missing_prerequisites": [["MAT2323"]]}},
    "already_passed": {"code": "already_passed", "course_code": "MAT2502", "data": {}},
    "block_limit_exceeded": {"code": "block_limit_exceeded", "course_code": "HIS1056",
                             "data": {"block_code": "II", "required_credits": 5, "earned_credits": 2,
                                      "planned_credits": 2, "course_credits": 3, "total_credits": 7}},
    "duplicate_course": {"code": "duplicate_course", "course_code": "MAT2502", "data": {"occurrence": 2}},
    "not_in_curriculum": {"code": "not_in_curriculum", "course_code": "XYZ999", "data": {}},
}


def _looks_clean(text):
    return text and text[0].isupper() and text.endswith(".") and not any(
        bad in text for bad in ("None", "nan", "{", "}", "  "))


def test_every_status_has_a_clean_sentence_that_names_the_course():
    assert set(SAMPLE_DETAILS) == set(STATUSES), "mỗi trạng thái của mục 4.1 phải có một ca mẫu"
    for status, detail in SAMPLE_DETAILS.items():
        text = status_text(_course("Giải tích 2", [["MAT2501"]]), detail, NAMES)
        assert _looks_clean(text) and "Giải tích 2" in text, (status, text)


def test_every_violation_has_a_clean_sentence_that_says_what_to_do():
    """Tiêu chí "hành động được" của README: sau dấu hai chấm luôn là việc người dùng cần làm."""
    assert set(SAMPLE_VIOLATIONS) == set(VIOLATIONS), "mỗi mã của mục 4.5 phải có một ca mẫu"
    for code, violation in SAMPLE_VIOLATIONS.items():
        whole_plan = code in ("credit_limit_exceeded", "credit_below_minimum", "not_in_curriculum")
        course = None if whole_plan else _course("Giải tích 2")
        text = violation_text(violation, course, NAMES)
        assert _looks_clean(text) and ": " in text, (code, text)
    assert "bỏ bớt ít nhất 3 tín chỉ" in violation_text(SAMPLE_VIOLATIONS["credit_limit_exceeded"], None, NAMES)


def test_the_credit_violations_of_a_self_entered_plan_name_the_window_the_student_set():
    """Mục 6.12: `credit_limit_exceeded` so với `max_credits` sinh viên đặt, `credit_below_minimum` với `min_credits`."""
    over = {"code": "credit_limit_exceeded", "course_code": "HIS1056",
            "data": {"max_credits": 20, "total_credits": 23}}
    assert violation_text(over, None, NAMES) == (
        "Kế hoạch có 23 tín chỉ, vượt mức tối đa 20 tín chỉ bạn đặt cho học kỳ này: cần bỏ bớt ít nhất 3 tín chỉ.")
    assert violation_text(SAMPLE_VIOLATIONS["credit_below_minimum"], None, NAMES) == (
        "Kế hoạch có 11 tín chỉ, chưa đủ mức tối thiểu 15 tín chỉ bạn đặt: cần thêm ít nhất 4 tín chỉ.")


def test_block_and_duplicate_violations_read_the_fields_the_rules_layer_sends():
    block = SAMPLE_VIOLATIONS["block_limit_exceeded"]
    assert violation_text(block, _course("Lịch sử văn minh thế giới"), NAMES) == (
        "Khối II chỉ cần 5 tín chỉ, thêm Lịch sử văn minh thế giới đưa tổng của khối lên 7: "
        "bỏ bớt môn của khối này.")
    named = {**block, "data": {**block["data"], "block_name": "Khối kiến thức theo lĩnh vực"}}
    assert violation_text(named, _course("Lịch sử văn minh thế giới"), NAMES).startswith(
        "Khối kiến thức theo lĩnh vực chỉ cần 5 tín chỉ")
    third = {"code": "duplicate_course", "course_code": "MAT2502", "data": {"occurrence": 3}}
    assert violation_text(third, _course("Giải tích 2"), NAMES) == \
        "Giải tích 2 xuất hiện lần thứ 3 trong kế hoạch: bỏ lần lặp này."


def test_unknown_codes_are_rejected():
    with pytest.raises(ValueError):
        status_text(_course("Giải tích 2"), {"status": "in_progress"}, NAMES)
    with pytest.raises(ValueError):
        violation_text({"code": "unknown", "course_code": "MAT2502", "data": {}}, None, NAMES)


def test_format_decimal_uses_a_comma_and_rounds():
    assert format_decimal(3) == "3,0"
    assert format_decimal(7.25, 2) == "7,25"
    assert format_decimal(8.96) == "9,0"


@pytest.mark.parametrize(("value", "expected"), [(5.25, "5,3"), (7.25, "7,3"), (2.45, "2,5"), (5.249, "5,2")])
def test_format_decimal_always_rounds_a_half_up(value, expected):
    """Python làm tròn 5,25 thành "5,2" nhưng 2,45 thành "2,5"; người đọc điểm chờ cả hai lên."""
    assert format_decimal(value) == expected


BLOCK_II = {"block_code": "II", "block_name": "Khối kiến thức theo lĩnh vực", "required_credits": 5}


@pytest.mark.parametrize(("course", "reason", "data", "expected"), [
    (_course("Giải tích 3"), "skipped", {}, "Bạn chọn chưa học Giải tích 3 ở kỳ này."),
    (_course("Nhập môn Robotic"), "block_full", {**BLOCK_II, "taken_credits": 5, "credits": 3},
     "Chưa xếp Nhập môn Robotic: khối kiến thức theo lĩnh vực chỉ cần 5 tín chỉ và đã có 5 từ môn đã đạt và "
     "môn xếp trên."),
    (_course("Phương trình vi phân"), "credit_budget", {"credits": 3, "total_credits": 20, "max_credits": 20},
     "Chưa xếp Phương trình vi phân: kỳ này đã có 20 tín chỉ, thêm 3 tín chỉ sẽ vượt mức tối đa 20 bạn đặt."),
])
def test_not_selected_texts_match_the_contract_example_word_for_word(course, reason, data, expected):
    assert not_selected_text(course, reason, data) == expected


def test_a_block_that_is_not_full_yet_says_why_the_course_still_does_not_fit():
    """Khối có 2/5, thêm môn 2 tín chỉ thành 4: khối chưa đầy, nên câu không được nói "đã có đủ"."""
    text = not_selected_text(_course("Nhập môn phân tích dữ liệu"), "block_full",
                             {**BLOCK_II, "taken_credits": 2, "credits": 2})
    assert text == ("Chưa xếp Nhập môn phân tích dữ liệu: khối kiến thức theo lĩnh vực cần đúng 5 tín chỉ, đã có 2; "
                    "thêm môn này (2 tín chỉ) thì phần còn thiếu không ghép đúng được bằng các môn còn lại.")


def test_every_not_selected_reason_has_a_clean_sentence_and_unknown_ones_raise():
    samples = {"skipped": {}, "block_full": {**BLOCK_II, "taken_credits": 5, "credits": 3},
               "credit_budget": {"credits": 3, "total_credits": 20, "max_credits": 20}}
    assert set(samples) == set(NOT_SELECTED_REASONS)
    for reason, data in samples.items():
        text = not_selected_text(_course("Giải tích 2"), reason, data)
        assert _looks_clean(text) and "Giải tích 2" in text, (reason, text)
    with pytest.raises(ValueError):
        not_selected_text(_course("Giải tích 2"), "unknown", {})


@pytest.mark.parametrize(("warning", "expected"), [
    ({"code": "below_min_credits", "data": {"min_credits": 10, "total_credits": 7}},
     "Chỉ xếp được 7 tín chỉ, thấp hơn mức tối thiểu 10 bạn đặt: không còn môn học được nào vừa với mức tối đa "
     "và luật khối tự chọn."),
    ({"code": "prerequisite_not_in_transcript", "course_code": "MAT2323",
      "data": {"missing_prerequisites": [["MAT2502"]]}},
     "Bảng điểm ghi đã đạt Xác suất - Thống kê nhưng chưa đạt Giải tích 2 (MAT2502): kiểm tra lại bảng điểm."),
    ({"code": "studied_before_prerequisite", "course_code": "MAT2323",
      "data": {"semester": 2, "prerequisite_code": "MAT2502", "prerequisite_semester": 2}},
     "Xác suất - Thống kê ghi học ở kỳ 2, không sau kỳ 2 của môn tiên quyết Giải tích 2 (MAT2502): kiểm tra lại "
     "kỳ học."),
])
def test_warning_texts_match_the_contract(warning, expected):
    assert warning_text(warning, NAMES) == expected


def test_every_warning_code_has_a_sentence_and_unknown_ones_raise():
    texts = [warning_text({"code": "below_min_credits", "data": {"min_credits": 10, "total_credits": 7}}, NAMES),
             warning_text({"code": "prerequisite_not_in_transcript", "course_code": "MAT2323",
                           "data": {"missing_prerequisites": [["MAT2502"]]}}, NAMES),
             warning_text({"code": "studied_before_prerequisite", "course_code": "MAT2323",
                           "data": {"semester": 2, "prerequisite_code": "MAT2502", "prerequisite_semester": 2}},
                          NAMES)]
    assert len(texts) == len(WARNINGS) and all(_looks_clean(text) for text in texts)
    with pytest.raises(ValueError):
        warning_text({"code": "unknown", "data": {}}, NAMES)


def test_the_credit_window_says_whether_the_total_reached_the_minimum():
    reached = credit_window_text({"min_credits": 15, "max_credits": 20, "total_credits": 20})
    short = credit_window_text({"min_credits": 10, "max_credits": 20, "total_credits": 7})
    assert reached == "Tổng 20 tín chỉ, trong khoảng 15–20 bạn đặt."
    assert short == "Tổng 7 tín chỉ, thấp hơn mức tối thiểu 10 bạn đặt."


def test_every_course_of_every_test_student_gets_a_clean_and_specific_sentence(repo_all):
    """Mọi dòng của `expected_course_status.csv`, đi qua đúng `rules.course_status_details()` như tầng API sẽ
    làm. Câu phải nêu tên môn thật, không lộ giá trị rỗng, và nêu đúng con số của đáp án viết tay: mọi mã
    tiên quyết còn thiếu, điểm của môn cần học lại."""
    expected = pd.read_csv("test/fixtures/students/expected_course_status.csv", dtype=str, keep_default_na=False)
    students = repo_all.students()
    errors, seen = [], set()
    for (university_code, student_code), rows in expected.groupby(["university_code", "student_code"]):
        student = students[(students["university_code"] == university_code)
                           & (students["student_code"] == student_code)].iloc[0]
        courses = {c["course_code"]: c for c in repo_all.curriculum_courses(student["curriculum_code"]).to_dict("records")}
        names = {code: course["course_name"] for code, course in courses.items()}
        details = course_status_details(repo_all, student)
        for row in rows.itertuples():
            course, detail = courses[row.course_code], details[row.course_code]
            text = status_text(course, detail, names)
            wanted = [course["course_name"], *filter(None, row.missing_prerequisites.split(";"))]
            if row.last_score:
                wanted.append(f"điểm {format_decimal(float(row.last_score))}")
            if not _looks_clean(text) or not all(part in text for part in wanted):
                errors.append((student_code, row.course_code, text))
            seen.add(detail["status"])
    assert seen == set(STATUSES), "sinh viên kiểm thử phải đi qua đủ năm trạng thái"
    assert not errors, f"{len(errors)} câu sai, ví dụ {errors[:3]}"
