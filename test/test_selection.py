"""Luật khối tự chọn khi chọn `k` học phần: chọn ĐÚNG `required_credits`, không thiếu đường, không vượt.

Không cần database. Các ca dựng theo hai khối thật của khung `HUS-7480113QTD-2022`: khối `II` cần 5 tín chỉ
gồm môn 2 và 3 tín chỉ, khối `V.3` cần 7 tín chỉ gồm khóa luận 7 tín chỉ hoặc hai môn 4 + 3 tín chỉ.
"""
from src.recommender.selection import fits_elective_block, pick_items, reachable_sums

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


def test_pick_items_does_not_modify_its_arguments():
    item = _item("HUS1022", 2)
    taken, open_courses = {"II": 0}, {"II": dict(BLOCK_II)}
    pick_items([(item, "II")], 5, {"II": 5}, taken, open_courses)
    assert item["rank"] is None
    assert taken == {"II": 0} and open_courses == {"II": BLOCK_II}
