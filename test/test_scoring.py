"""Test cho sáu tiêu chí xếp hạng (hợp đồng mục 4.4, 6.6).

Không cần database: mọi hàm trong `src/recommender/scoring.py` chỉ nhận dict tự gõ. Hai test cuối
dựng lại đúng hai ví dụ phản hồi của mục 6.6 (score 5,5 và 2,75), nên khi đổi công thức mà quên
cập nhật hợp đồng thì chúng đỏ.
"""
import pytest

from src import recommender
from src.recommender import scoring

W = scoring.DEFAULT_WEIGHTS
TOPIC = {"topic_code": "toan", "topic_name": "Toán", "average_score": 8.5, "course_codes": ["B", "A"]}
PASS_SCORE, MAX_SCORE = 4.0, 10


def _all_reasons(weights):
    """Gọi cả sáu tiêu chí với một bộ dữ liệu mà tiêu chí nào cũng áp dụng."""
    return [
        scoring.outstanding_retake({"term_code": "20252", "score": 3.0, "attempt_no": 1}, weights),
        scoring.schedule(2, 3, weights),
        scoring.schedule(3, 3, weights),
        scoring.unlocks("A", {"B": [["A"]]}, weights),
        scoring.strong_topic({**TOPIC, "average_score": 10.0}, PASS_SCORE, MAX_SCORE, weights),
        scoring.interest({"topic_code": "toan", "topic_name": "Toán", "weight": 1.0}, weights),
    ]


# ---------------- Bảng trọng số ----------------

def test_merge_weights_returns_a_copy_of_the_defaults_when_nothing_is_sent():
    assert scoring.merge_weights() == W
    assert scoring.merge_weights({}) == W
    assert scoring.merge_weights() is not W


def test_merge_weights_fills_missing_keys_from_the_defaults():
    merged = scoring.merge_weights({"unlocks": 0.25})
    assert merged["unlocks"] == 0.25
    assert merged["outstanding_retake"] == W["outstanding_retake"]
    assert set(merged) == set(W)


@pytest.mark.parametrize("weights", [{"unknown": 1.0}, {"Unlocks": 1.0}, {"unlocks": 1.0, "x": 0}])
def test_merge_weights_rejects_unknown_keys(weights):
    with pytest.raises(ValueError):
        scoring.merge_weights(weights)


@pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf"), "cao", None])
def test_merge_weights_rejects_values_that_are_not_a_number_at_least_zero(value):
    with pytest.raises(ValueError):
        scoring.merge_weights({"unlocks": value})


def test_zero_weight_is_allowed_and_every_criterion_applies_in_the_sample():
    assert {reason["code"] for reason in _all_reasons(W)} == set(W)
    assert scoring.merge_weights({"interest": 0})["interest"] == 0


@pytest.mark.parametrize("code", sorted(W))
def test_zero_weight_removes_the_reason_instead_of_contributing_nothing(code):
    """Mục 4.4: tiêu chí không góp điểm thì vắng mặt, KHÔNG trả về contribution = 0."""
    reasons = _all_reasons({**W, code: 0.0})
    assert code not in {reason["code"] for reason in reasons if reason}


# ---------------- Môn đang nợ ----------------

def test_outstanding_retake_is_absent_when_the_course_is_not_outstanding():
    assert scoring.outstanding_retake(None, W) is None


def test_outstanding_retake_matches_the_contract_example():
    assert scoring.outstanding_retake({"term_code": "20252", "score": 3.0, "attempt_no": 1}, W) == {
        "code": "outstanding_retake", "contribution": 3.0,
        "text": "Bạn chưa đạt môn này ở học kỳ 20252 (điểm 3,0).",
        "data": {"term_code": "20252", "score": 3.0, "attempt_no": 1},
    }


def test_outstanding_retake_omits_the_score_when_the_attempt_has_none():
    reason = scoring.outstanding_retake({"term_code": "20252", "score": None, "attempt_no": 2}, W)
    assert "score" not in reason["data"]          # mục 3.2: trường vô nghĩa thì vắng mặt, không null
    assert reason["text"] == "Bạn chưa đạt môn này ở học kỳ 20252."


# ---------------- Đúng kỳ và trễ kỳ ----------------

def test_on_time_matches_the_contract_example():
    assert scoring.schedule(3, 3, W) == {
        "code": "on_time", "contribution": 2.0,
        "text": "Đúng kỳ dự kiến của chương trình (kỳ 3).",
        "data": {"recommended_semester": 3, "target_semester": 3},
    }


def test_overdue_matches_the_contract_example():
    assert scoring.schedule(2, 3, W) == {
        "code": "overdue", "contribution": 1.0,
        "text": "Môn này dự kiến học ở kỳ 2, bạn đang ở kỳ 3.",
        "data": {"recommended_semester": 2, "target_semester": 3, "semesters_late": 1},
    }


@pytest.mark.parametrize(("semesters_late", "contribution"), [(1, 1.0), (2, 2.0), (3, 2.0), (7, 2.0)])
def test_overdue_saturates_after_two_semesters(semesters_late, contribution):
    assert scoring.schedule(1, 1 + semesters_late, W)["contribution"] == contribution


def test_a_course_planned_for_a_later_semester_gets_no_schedule_reason():
    assert scoring.schedule(5, 3, W) is None


@pytest.mark.parametrize("recommended", range(1, 9))
def test_on_time_and_overdue_are_mutually_exclusive(recommended):
    reason = scoring.schedule(recommended, 4, W)
    if recommended == 4:
        assert reason["code"] == "on_time"
    elif recommended < 4:
        assert reason["code"] == "overdue"
    else:
        assert reason is None


# ---------------- Mở khóa môn khác ----------------

def test_unlocks_reaches_full_weight_at_ten_courses():
    groups = {f"C{index}": [["MAT2505"]] for index in range(12)}
    reason = scoring.unlocks("MAT2505", groups, W)
    assert reason["contribution"] == 1.5
    assert reason["data"]["count"] == 12
    assert reason["text"] == "Đạt môn này sẽ mở khóa 12 học phần khác của chương trình."


def test_unlocks_is_proportional_below_the_saturation_point():
    groups = {f"C{index}": [["MAT2323"]] for index in range(5)}
    assert scoring.unlocks("MAT2323", groups, W)["contribution"] == 0.75


def test_unlocks_is_absent_when_no_course_depends_on_this_one():
    assert scoring.unlocks("X", {"A": [["B"]], "B": []}, W) is None


def test_unlocks_counts_alternatives_inside_a_group_and_sorts_the_codes():
    groups = {"B": [["X", "A"]], "C": [["Z"], ["A"]], "A": [], "D": [["Y"]]}
    assert scoring.unlocks("A", groups, W)["data"]["course_codes"] == ["B", "C"]


# ---------------- Chủ đề học tốt và sở thích tự khai ----------------

@pytest.mark.parametrize(("average_score", "level"),
                         [(4.0, 0.0), (5.5, 0.25), (7.0, 0.5), (10.0, 1.0), (2.0, 0.0), (11.0, 1.0)])
def test_topic_strength_normalises_the_excess_above_the_pass_score(average_score, level):
    assert scoring.topic_strength(average_score, PASS_SCORE, MAX_SCORE) == pytest.approx(level)


def test_topic_strength_survives_a_degenerate_grading_scheme():
    assert scoring.topic_strength(10, 10, 10) == 0.0


def test_strong_topic_is_absent_exactly_at_the_pass_score():
    assert scoring.strong_topic({**TOPIC, "average_score": PASS_SCORE},
                                PASS_SCORE, MAX_SCORE, W) is None


def test_strong_topic_is_absent_when_the_course_has_no_topic():
    assert scoring.strong_topic(None, PASS_SCORE, MAX_SCORE, W) is None


def test_strong_topic_scales_with_the_average_score():
    reason = scoring.strong_topic(TOPIC, PASS_SCORE, MAX_SCORE, W)
    assert reason["contribution"] == 0.75
    assert reason["data"] == {"topic_code": "toan", "topic_name": "Toán",
                              "average_score": 8.5, "course_codes": ["A", "B"]}
    assert "8,5" in reason["text"]


@pytest.mark.parametrize(("declared", "contribution"), [(1.0, 0.5), (0.5, 0.25), (0.2, 0.1)])
def test_interest_scales_with_the_declared_weight(declared, contribution):
    reason = scoring.interest({"topic_code": "toan", "topic_name": "Toán", "weight": declared}, W)
    assert reason["contribution"] == contribution
    assert reason["data"]["weight"] == declared


def test_interest_is_absent_when_the_student_declared_nothing_for_the_topic():
    assert scoring.interest(None, W) is None


def test_the_declared_interest_can_never_outweigh_the_study_results():
    """Mục 4.4: kết quả học tập là tín hiệu chính, lời khai là tín hiệu phụ."""
    best_interest = scoring.interest({"topic_code": "toan", "topic_name": "Toán", "weight": 1.0}, W)
    best_strong = scoring.strong_topic({**TOPIC, "average_score": MAX_SCORE},
                                       PASS_SCORE, MAX_SCORE, W)
    assert best_interest["contribution"] < best_strong["contribution"]


# ---------------- Ghép điểm và sắp lý do ----------------

def test_sort_reasons_drops_criteria_that_do_not_apply_and_breaks_ties_by_code():
    reasons = scoring.sort_reasons([
        None,
        {"code": "unlocks", "contribution": 1.5},
        {"code": "overdue", "contribution": 2.0},
        {"code": "interest", "contribution": 1.5},
    ])
    assert [reason["code"] for reason in reasons] == ["overdue", "interest", "unlocks"]


def test_total_score_rounds_to_four_digits():
    assert scoring.total_score([{"contribution": 0.1}, {"contribution": 0.2}]) == 0.3
    assert scoring.total_score([]) == 0


@pytest.mark.parametrize(("year_of_study", "term_no", "expected"),
                         [(1, 1, 1), (1, 2, 2), (2, 1, 3), (2, 2, 4), (4, 2, 8)])
def test_target_semester_maps_year_and_term_to_a_position_in_the_curriculum(
        year_of_study, term_no, expected):
    assert scoring.target_semester(year_of_study, term_no) == expected


def test_target_semester_of_the_contract_example():
    """T03 nhập học khóa 2025, học kỳ cần gợi ý là 20261 (năm học 2026–2027, kỳ 1): kỳ thứ 3."""
    assert scoring.target_semester(2026 - 2025 + 1, 1) == 3


# ---------------- Hai ví dụ của mục 6.6 ----------------

def test_the_first_contract_example_adds_up_to_5_5():
    """MAT2505: đang nợ từ kỳ 20252, trễ một kỳ, mở khóa 12 học phần."""
    reasons = scoring.sort_reasons([
        scoring.outstanding_retake({"term_code": "20252", "score": 3.0, "attempt_no": 1}, W),
        scoring.schedule(2, 3, W),
        scoring.unlocks("MAT2505", {f"C{index}": [["MAT2505"]] for index in range(12)}, W),
    ])
    assert [reason["code"] for reason in reasons] == ["outstanding_retake", "unlocks", "overdue"]
    assert [reason["contribution"] for reason in reasons] == [3.0, 1.5, 1.0]
    assert scoring.total_score(reasons) == 5.5


def test_the_second_contract_example_adds_up_to_2_75():
    """MAT2323: đúng kỳ dự kiến, mở khóa 5 học phần."""
    reasons = scoring.sort_reasons([
        scoring.schedule(3, 3, W),
        scoring.unlocks("MAT2323", {f"C{index}": [["MAT2323"]] for index in range(5)}, W),
    ])
    assert [reason["code"] for reason in reasons] == ["on_time", "unlocks"]
    assert [reason["contribution"] for reason in reasons] == [2.0, 0.75]
    assert scoring.total_score(reasons) == 2.75


def test_the_package_publishes_the_algorithm_constants_the_api_reads():
    """Tầng API đọc hai hằng số này cho GET /v1/meta (mục 6.1)."""
    assert recommender.ALGORITHM == "rule_based_weighted"
    assert recommender.ALGORITHM_VERSION == "1.0.1"
