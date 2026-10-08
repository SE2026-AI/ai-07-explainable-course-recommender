"""Hợp đồng cho thuật toán gợi ý – chạy khi package src/recommender có hàm `recommend`.

Thuật toán cần có hàm (xuất ra ở src/recommender/__init__.py):
    recommend(repo, student, k=5) -> list[dict]   # mỗi dict có ít nhất "course_code"
trong đó `student` là một dòng của repo.students().

Gợi ý dựa trên DỮ LIỆU HỌC TẬP của sinh viên (môn đã đạt/trượt, điểm, tiến độ, tiên quyết);
sở thích tự khai chỉ là tín hiệu phụ. Các test đánh dấu xfail là luật app CHƯA làm; làm xong thì bỏ dấu xfail.
"""
import pandas as pd
import pytest

rec = pytest.importorskip("src.recommender")
if not hasattr(rec, "recommend"):
    pytest.skip("src/recommender chưa có hàm recommend()", allow_module_level=True)
EXP = pd.read_csv("test/fixtures/students/expected_course_status.csv", keep_default_na=False, dtype=str)
STATUS = {(r.university_code, r.student_code, r.course_code): r.expected_status for r in EXP.itertuples()}
CASES = [tuple(x) for x in EXP[["university_code", "student_code"]].drop_duplicates().values]


def _run(repo, uni, code):
    sv = repo.students()
    s = sv[(sv["university_code"] == uni) & (sv["student_code"] == code)].iloc[0]
    return s, [x["course_code"] for x in rec.recommend(repo, s)]


@pytest.mark.parametrize("uni,code", CASES)
def test_chi_goi_y_mon_hoc_duoc_trong_khung(repo_all, uni, code):
    _, ds = _run(repo_all, uni, code)
    sai = [(m, STATUS.get((uni, code, m), "không thuộc khung")) for m in ds
           if STATUS.get((uni, code, m)) not in ("eligible", "retake")]
    assert not sai, sai


@pytest.mark.xfail(reason="Chưa làm: ưu tiên môn cần học lại", strict=False)
@pytest.mark.parametrize("uni,code", [c for c in CASES if any(STATUS.get((*c, m)) == "retake"
                                                             for m in EXP["course_code"])])
def test_goi_y_mon_can_hoc_lai(repo_all, uni, code):
    _, ds = _run(repo_all, uni, code)
    can = {m for (u, c, m), st in STATUS.items() if (u, c) == (uni, code) and st == "retake"}
    assert can <= set(ds)


@pytest.mark.xfail(reason="Chưa làm: không gợi ý vượt số tín chỉ khối tự chọn", strict=False)
def test_khong_vuot_khoi_tu_chon_tren_toan_bo_sinh_vien(repo):
    loi = []
    for cur, d in repo.students().groupby("curriculum_code"):
        c = repo.curriculum_courses(cur).set_index("course_code")
        need = repo.elective_blocks(cur).set_index("block_code")["required_credits"]
        for _, s in d.iterrows():
            ds = [x["course_code"] for x in rec.recommend(repo, s)]
            done = {}
            for m in list(s["passed_courses"]) + ds:
                b = c.loc[m, "elective_block"]
                if isinstance(b, str):
                    if m in ds and done.get(b, 0) >= need[b]:
                        loi.append((s["student_code"], m, b))
                    done[b] = done.get(b, 0) + c.loc[m, "credits"]
    assert not loi, f"{len(loi)} lỗi, ví dụ {loi[:5]}"


@pytest.mark.xfail(reason="Chưa làm: ưu tiên môn tự chọn thuộc chủ đề sinh viên học giỏi", strict=False)
def test_goi_y_tu_chon_theo_diem_manh(repo_all):
    """T16 giỏi chủ đề Dữ liệu, T17 giỏi Toán, còn lại như nhau và không khai sở thích.
    Trong các môn tự chọn được gợi ý, tỷ lệ môn thuộc chủ đề mạnh phải cao hơn tỷ lệ đó trong
    tất cả môn tự chọn sinh viên học được."""
    for code, manh in [("T16", "du_lieu"), ("T17", "toan")]:
        s, ds = _run(repo_all, "HUS", code)
        c = repo_all.curriculum_courses(s["curriculum_code"]).set_index("course_code")
        tu_chon = [m for m in c.index if isinstance(c.loc[m, "elective_block"], str)]
        hoc_duoc = [m for m in tu_chon if STATUS.get(("HUS", code, m)) == "eligible"]
        goi_y = [m for m in ds if m in tu_chon]
        manh_hd = sum(c.loc[m, "primary_topic"] == manh for m in hoc_duoc) / len(hoc_duoc)
        manh_gy = sum(c.loc[m, "primary_topic"] == manh for m in goi_y) / len(goi_y) if goi_y else 0
        assert goi_y and manh_gy > manh_hd, (code, goi_y)


def test_hai_sinh_vien_chi_khac_nhom_cong_bang_co_cung_goi_y(repo_all):
    assert _run(repo_all, "HUS", "T02")[1] == _run(repo_all, "HUS", "T08")[1]
