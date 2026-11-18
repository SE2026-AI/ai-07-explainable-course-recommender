"""Luật khối tự chọn khi chọn học phần: chọn ĐÚNG `required_credits`, không thiếu đường, không vượt. Áp cho
cả hai cách chọn: nhiều nhất `k` môn (`pick_items`) và trong khoảng tín chỉ (`pick_within_credits`).

Không cần database. Các ca dựng theo hai khối thật của khung `HUS-7480113QTD-2022`: khối `II` cần 5 tín chỉ
gồm môn 2 và 3 tín chỉ, khối `V.3` cần 7 tín chỉ gồm khóa luận 7 tín chỉ hoặc hai môn 4 + 3 tín chỉ.
"""
from src.recommender.selection import fits_elective_block, pick_items, pick_within_credits, reachable_sums
from src.rules.status import fits_in_block

BLOCK_II = {"HUS1021": 3, "HUS1022": 2, "HUS1023": 2, "HUS1024": 3, "HIS1056": 3}
BLOCK_V3 = {"MAT4080": 7, "MAT1203": 4, "MAT3377": 3}


def _item(code, credits):
    return {"rank": None, "course_code": code, "credits": credits}


def _codes(picked):
    return [item["course_code"] for item in picked]


def test_reachable_sums_uses_each_course_at_most_once():
    assert reachable_sums([]) == {0}
    assert reachable_sums([2, 3]) == {0, 2, 3, 5}
    assert 4 not in reachable_sums([2, 3]), "một môn 2 tín chỉ không được dùng hai lần"


def test_a_course_that_overshoots_the_block_does_not_fit():
    assert not fits_elective_block(3, 3, 5, [2, 2])


def test_a_course_that_leaves_an_unfillable_gap_does_not_fit():
    """Đã có 2, thêm môn 2 nữa thành 4: còn thiếu 1 mà các môn còn lại đều 3 tín chỉ."""
    assert not fits_elective_block(2, 2, 5, [3, 3, 3])
    assert fits_elective_block(3, 2, 5, [3, 3])


def test_a_course_that_completes_the_block_exactly_fits():
    assert fits_elective_block(7, 0, 7, [3, 4])
    assert fits_elective_block(4, 3, 7, [7])


def test_selection_never_accepts_a_course_the_rules_layer_says_overshoots():
    """`recommend()` và `plan-check` không được nói ngược nhau: môn nào tầng xếp hạng nhận thì cũng qua được
    `rules.fits_in_block()`, dù các môn còn lại của khối là gì."""
    for required in range(1, 9):
        for taken in range(required + 1):
            for credits in range(1, 8):
                if not fits_in_block(credits, taken, required):
                    assert not fits_elective_block(credits, taken, required, [1, 2, 3, 4]), (credits, taken, required)


def test_the_regression_case_two_two_three_now_picks_two_three():
    """Bản 1.0.0 nhận cả ba môn của khối II và lên 7/5 tín chỉ — ca hay gặp nhất trong `data/synthetic`."""
    ranked = [(_item("HUS1022", 2), "II"), (_item("HUS1023", 2), "II"), (_item("HIS1056", 3), "II")]
    picked = pick_items(ranked, 5, {"II": 5}, {}, {"II": BLOCK_II})
    assert _codes(picked) == ["HUS1022", "HIS1056"]
    assert sum(item["credits"] for item in picked) == 5


def test_credits_already_passed_count_towards_the_block():
    ranked = [(_item("HUS1023", 2), "II"), (_item("HIS1056", 3), "II")]
    open_courses = {"II": {code: c for code, c in BLOCK_II.items() if code != "HUS1022"}}
    picked = pick_items(ranked, 5, {"II": 5}, {"II": 2}, open_courses)
    assert _codes(picked) == ["HIS1056"]


def test_the_thesis_block_takes_the_thesis_or_the_pair_never_both():
    thesis_first = [(_item("MAT4080", 7), "V.3"), (_item("MAT1203", 4), "V.3"), (_item("MAT3377", 3), "V.3")]
    assert _codes(pick_items(thesis_first, 5, {"V.3": 7}, {}, {"V.3": BLOCK_V3})) == ["MAT4080"]
    pair_first = [(_item("MAT1203", 4), "V.3"), (_item("MAT4080", 7), "V.3"), (_item("MAT3377", 3), "V.3")]
    assert _codes(pick_items(pair_first, 5, {"V.3": 7}, {}, {"V.3": BLOCK_V3})) == ["MAT1203", "MAT3377"]


def test_skipped_courses_do_not_use_up_the_limit_and_ranks_stay_continuous():
    ranked = [(_item("HUS1022", 2), "II"), (_item("HUS1023", 2), "II"), (_item("MAT2505", 3), None),
              (_item("HIS1056", 3), "II"), (_item("MAT2323", 4), None)]
    picked = pick_items(ranked, 3, {"II": 5}, {}, {"II": BLOCK_II})
    assert _codes(picked) == ["HUS1022", "MAT2505", "HIS1056"]
    assert [item["rank"] for item in picked] == [1, 2, 3]


def test_courses_outside_elective_blocks_are_never_filtered():
    ranked = [(_item(f"C{i}", 3), None) for i in range(4)]
    assert _codes(pick_items(ranked, 10, {}, {}, {})) == ["C0", "C1", "C2", "C3"]


def test_a_chosen_course_always_gets_a_place_and_keeps_its_ranked_position():
    ranked = [(_item(f"C{i}", 3), None) for i in range(6)]
    picked = pick_items(ranked, 3, {}, {}, {}, chosen={"C5"})
    assert _codes(picked) == ["C0", "C1", "C5"]
    assert [item["rank"] for item in picked] == [1, 2, 3]


def test_a_chosen_course_takes_its_elective_block_before_higher_ranked_courses():
    """Đã đạt HUS1022 (2 tín chỉ) của khối II: chọn HUS1024 thì 3 tín chỉ còn lại thuộc về nó, HUS1021 hết chỗ."""
    ranked = [(_item("HUS1021", 3), "II"), (_item("MAT2505", 3), None), (_item("HUS1024", 3), "II")]
    open_courses = {"II": {code: c for code, c in BLOCK_II.items() if code != "HUS1022"}}
    picked = pick_items(ranked, 5, {"II": 5}, {"II": 2}, open_courses, chosen={"HUS1024"})
    assert _codes(picked) == ["MAT2505", "HUS1024"]


def test_a_chosen_course_that_would_break_its_block_is_left_out_for_the_caller_to_report():
    ranked = [(_item("MAT2505", 3), None), (_item("HUS1023", 2), "II")]
    open_courses = {"II": {code: c for code, c in BLOCK_II.items() if code != "HUS1022"}}
    picked = pick_items(ranked, 5, {"II": 5}, {"II": 2}, open_courses, chosen={"HUS1023"})
    assert _codes(picked) == ["MAT2505"]


def test_pick_items_does_not_modify_its_arguments():
    item = _item("HUS1022", 2)
    taken, open_courses = {"II": 0}, {"II": dict(BLOCK_II)}
    pick_items([(item, "II")], 5, {"II": 5}, taken, open_courses)
    assert item["rank"] is None
    assert taken == {"II": 0} and open_courses == {"II": BLOCK_II}


# Chọn trong khoảng tín chỉ (mục 6.11).

def _left_out(left_out):
    return [(item["course_code"], reason) for item, reason, _ in left_out]


def test_within_credits_stops_by_credits_and_keeps_scanning_past_a_course_that_does_not_fit():
    """Còn trống 2 tín chỉ thì môn 3 tín chỉ không vào, nhưng môn 2 tín chỉ xếp dưới nó vẫn vào."""
    ranked = [(_item("A", 4), None), (_item("B", 4), None), (_item("C", 3), None), (_item("D", 2), None)]
    items, left_out = pick_within_credits(ranked, 10, {}, {}, {})
    assert _codes(items) == ["A", "B", "D"]
    assert [item["rank"] for item in items] == [1, 2, 3]
    assert _left_out(left_out) == [("C", "credit_budget")]
    assert left_out[0][2] == {"credits": 3, "total_credits": 10, "max_credits": 10}


def test_within_credits_applies_the_elective_block_rule_before_the_budget():
    """Đã đạt HUS1022 (2/5 tín chỉ của khối II). HIS1056 (3) hoàn thành khối; HUS1023 (2) sau đó vượt khối, dù
    còn thừa tín chỉ: lý do phải là `block_full`, không phải `credit_budget`."""
    ranked = [(_item("HIS1056", 3), "II"), (_item("HUS1023", 2), "II"), (_item("MAT2505", 3), None)]
    open_courses = {"II": {code: c for code, c in BLOCK_II.items() if code != "HUS1022"}}
    items, left_out = pick_within_credits(ranked, 20, {"II": 5}, {"II": 2}, open_courses)
    assert _codes(items) == ["HIS1056", "MAT2505"]
    assert _left_out(left_out) == [("HUS1023", "block_full")]
    assert left_out[0][2] == {"block_code": "II", "required_credits": 5, "taken_credits": 5, "credits": 2}


def test_within_credits_refuses_a_course_that_leaves_an_unfillable_gap():
    """Khối II chưa có gì: nhận HUS1022 (2) rồi HUS1023 (2) thành 4, còn thiếu 1 mà không môn nào 1 tín chỉ."""
    ranked = [(_item("HUS1022", 2), "II"), (_item("HUS1023", 2), "II"), (_item("HUS1021", 3), "II")]
    items, left_out = pick_within_credits(ranked, 20, {"II": 5}, {"II": 0}, {"II": dict(BLOCK_II)})
    assert _codes(items) == ["HUS1022", "HUS1021"]
    assert _left_out(left_out) == [("HUS1023", "block_full")]


def test_within_credits_never_takes_a_skipped_course_but_keeps_it_in_ranked_order():
    ranked = [(_item("A", 3), None), (_item("B", 3), None), (_item("C", 3), None), (_item("D", 3), None)]
    items, left_out = pick_within_credits(ranked, 6, {}, {}, {}, skipped={"B"})
    assert _codes(items) == ["A", "C"]
    assert _left_out(left_out) == [("B", "skipped"), ("D", "credit_budget")]
    assert left_out[0][2] == {}


def test_within_credits_takes_an_included_course_first_and_ranks_it_by_its_place():
    """Chỉ đủ chỗ cho hai môn: môn muốn học D chiếm chỗ trước, đẩy B ra, nhưng vẫn đứng sau A trong `items`."""
    ranked = [(_item("A", 3), None), (_item("B", 3), None), (_item("C", 3), None), (_item("D", 3), None)]
    items, left_out = pick_within_credits(ranked, 6, {}, {}, {}, chosen={"D"})
    assert _codes(items) == ["A", "D"]
    assert [item["rank"] for item in items] == [1, 2]
    assert _left_out(left_out) == [("B", "credit_budget"), ("C", "credit_budget")]


def test_within_credits_leaves_out_an_included_course_that_breaks_its_block_for_the_caller_to_report():
    ranked = [(_item("MAT2505", 3), None), (_item("HUS1023", 2), "II")]
    open_courses = {"II": {code: c for code, c in BLOCK_II.items() if code != "HUS1022"}}
    items, left_out = pick_within_credits(ranked, 20, {"II": 5}, {"II": 2}, open_courses, chosen={"HUS1023"})
    assert _codes(items) == ["MAT2505"]
    assert _left_out(left_out) == [("HUS1023", "block_full")]


def test_within_credits_reports_the_final_totals_in_every_reason():
    """`total_credits` và `taken_credits` là số SAU khi xếp xong, kể cả với môn bị từ chối sớm."""
    ranked = [(_item("A", 8), None), (_item("B", 8), None), (_item("C", 2), None), (_item("D", 1), None)]
    items, left_out = pick_within_credits(ranked, 10, {}, {}, {})
    assert _codes(items) == ["A", "C"]
    assert [data["total_credits"] for _, _, data in left_out] == [10, 10]


def test_within_credits_puts_every_candidate_in_exactly_one_list():
    ranked = [(_item(code, credits), "II" if code in BLOCK_II else None)
              for code, credits in [("HIS1056", 3), ("MAT2505", 3), ("HUS1024", 3), ("MAT2323", 4),
                                    ("HUS1023", 2), ("MAT2503", 2), ("PHI1002", 2), ("MAT4080", 7)]]
    open_courses = {"II": {code: c for code, c in BLOCK_II.items() if code != "HUS1022"}}
    items, left_out = pick_within_credits(ranked, 12, {"II": 5}, {"II": 2}, open_courses, skipped={"MAT2503"})
    codes = _codes(items) + [code for code, _ in _left_out(left_out)]
    assert sorted(codes) == sorted(item["course_code"] for item, _ in ranked)
    assert sum(item["credits"] for item in items) <= 12


def test_pick_within_credits_does_not_modify_its_arguments():
    item = _item("HUS1022", 2)
    taken, open_courses = {"II": 0}, {"II": dict(BLOCK_II)}
    pick_within_credits([(item, "II")], 10, {"II": 5}, taken, open_courses)
    assert item["rank"] is None
    assert taken == {"II": 0} and open_courses == {"II": BLOCK_II}
