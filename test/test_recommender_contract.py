"""Hợp đồng cho thuật toán gợi ý `src.recommender.recommend(repo, student, k)`.

`student` là một dòng của repo.students(). Gợi ý dựa trên DỮ LIỆU HỌC TẬP của sinh viên (môn đã
đạt/trượt, điểm, tiến độ, tiên quyết); sở thích tự khai chỉ là tín hiệu phụ. Công thức của từng tiêu chí
ở docs/architecture/ranking.md.

Import thẳng, không `importorskip`: module này đã có trên main, nên nếu nó vỡ thì bộ test này phải đỏ
chứ không được lặng lẽ bỏ qua.
"""
from itertools import combinations

import pandas as pd
import pytest

import src.recommender as rec

EXP = pd.read_csv("test/fixtures/students/expected_course_status.csv", keep_default_na=False, dtype=str)
STATUS = {(r.university_code, r.student_code, r.course_code): r.expected_status for r in EXP.itertuples()}
CASES = [tuple(x) for x in EXP[["university_code", "student_code"]].drop_duplicates().values]


def _run(repo, uni, code, k=5):
    sv = repo.students()
    s = sv[(sv["university_code"] == uni) & (sv["student_code"] == code)].iloc[0]
    return s, [x["course_code"] for x in rec.recommend(repo, s, k=k)]


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


def _can_fill_exactly(gap, credits):
    """Ghép được đúng `gap` tín chỉ từ `credits`, mỗi môn dùng một lần. Viết độc lập với
    `src/recommender/selection.py` để test không lặp lại chính code nó kiểm."""
    return any(sum(chosen) == gap for size in range(len(credits) + 1) for chosen in combinations(credits, size))


@pytest.mark.parametrize("dataset", ["repo", "repo_all"])
def test_elective_blocks_stay_exactly_completable_for_every_student(request, dataset):
    """Khối `choose_credits` phải chọn ĐÚNG `required_credits` (hợp đồng mục 6.2). Với mọi sinh viên, tín
    chỉ đã đạt cộng tín chỉ được gợi ý trong mỗi khối không vượt `required_credits`, và phần còn thiếu
    vẫn ghép đúng được từ các môn chưa đạt, chưa được gợi ý của khối.

    Kiểm tổng sau cùng chứ không kiểm từng bước chọn. Bản trước kiểm "khối đã đủ thì bỏ" — đúng như code
    đã viết — nên không bắt được việc gợi ý 2 + 2 + 3 tín chỉ cho khối cần 5 (54/200 sinh viên)."""
    repo = request.getfixturevalue(dataset)
    errors = []
    for curriculum, group in repo.students().groupby("curriculum_code"):
        courses = repo.curriculum_courses(curriculum).set_index("course_code")
        required = repo.elective_blocks(curriculum).set_index("block_code")["required_credits"]
        for _, student in group.iterrows():
            passed = set(student["passed_courses"])
            picked = {item["course_code"] for item in rec.recommend(repo, student, k=20)}
            for block, need in required.items():
                members = courses[courses["elective_block"] == block]["credits"]
                total = int(members[members.index.isin(passed | picked)].sum())
                rest = [int(c) for code, c in members.items() if code not in passed | picked]
                if total > need or not _can_fill_exactly(int(need) - total, rest):
                    errors.append((student["student_code"], block, f"{total}/{need}"))
    assert not errors, f"{len(errors)} lỗi, ví dụ {errors[:5]}"


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
