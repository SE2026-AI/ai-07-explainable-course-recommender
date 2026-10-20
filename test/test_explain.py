"""Câu chữ của tầng giải thích: khớp từng chữ với ví dụ của hợp đồng, giữ đúng VÀ/HOẶC, không lộ giá trị rỗng.

Không cần database: tên học phần lấy nguyên từ ví dụ ở mục 6.5 và 6.7 của `api-contract.md`.
"""
import pytest

from src.explain import (
    STATUSES,
    VIOLATIONS,
    format_decimal,
    prerequisite_phrase,
    status_text,
    violation_text,
)

NAMES = {"MAT2323": "Xác suất - Thống kê", "MAT2502": "Giải tích 2", "MAT3507": "Cơ sở dữ liệu",
         "MAT2505": "Lập trình cơ bản", "CS101": "Nhập môn lập trình", "HUS1011": "Tin học cơ sở"}


def _course(name, groups=None):
    return {"course_name": name, "prerequisite_groups": groups or []}


@pytest.mark.parametrize(("course", "detail", "expected"), [
    (_course("Lập trình cơ bản", [["HUS1011"]]),
     {"status": "retake", "last_attempt": {"term_code": "20252", "attempt_no": 1, "score": 3.0, "letter_grade": "F"}},
     "Cần học lại Lập trình cơ bản: bạn chưa đạt môn này ở học kỳ 20252 (điểm 3,0)."),
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
SAMPLE_VIOLATIONS = {
    "credit_limit_exceeded": {"code": "credit_limit_exceeded", "course_code": None,
                              "data": {"total_credits": 24, "max_credits_per_term": 21}},
    "missing_prerequisite": {"code": "missing_prerequisite", "course_code": "MAT3533",
                             "data": {"missing_prerequisites": [["MAT2323"]]}},
    "already_passed": {"code": "already_passed", "course_code": "MAT2502", "data": {}},
    "block_limit_exceeded": {"code": "block_limit_exceeded", "course_code": "HIS1056",
                             "data": {"block_name": "Khối kiến thức theo lĩnh vực", "required_credits": 5,
                                      "planned_credits": 7}},
    "duplicate_course": {"code": "duplicate_course", "course_code": "MAT2502", "data": {"count": 2}},
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
        course = None if code in ("credit_limit_exceeded", "not_in_curriculum") else _course("Giải tích 2")
        text = violation_text(violation, course, NAMES)
        assert _looks_clean(text) and ": " in text, (code, text)
    assert "bỏ bớt ít nhất 3 tín chỉ" in violation_text(SAMPLE_VIOLATIONS["credit_limit_exceeded"], None, NAMES)


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
