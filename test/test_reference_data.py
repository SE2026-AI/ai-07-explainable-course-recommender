"""Dữ liệu tham chiếu (trường, ngành, khung, học phần…) đúng với văn bản và tự nhất quán.
Mọi bài chạy cho MỌI khung CTĐT có trong dữ liệu."""
from itertools import combinations

import pytest
from conftest import curricula_codes

CURRICULA = curricula_codes()


@pytest.fixture(scope="module")
def blocks(repo_all):
    return repo_all._q("""SELECT c.code AS curriculum_code, b.id, b.code, b.parent_block_id, b.selection_rule,
                                 b.required_credits, b.counts_toward_total
                          FROM curriculum_blocks b JOIN curricula c ON c.id = b.curriculum_id""")


@pytest.mark.parametrize("cur", CURRICULA)
def test_tong_tin_chi_khop_van_ban(repo_all, cur):
    c = repo_all.curriculum_courses(cur)
    bat_buoc = c[(c["selection_rule"] == "all") & (c["counts_toward_total"] == 1)]["credits"].sum()
    tu_chon = repo_all.elective_blocks(cur)["required_credits"].sum()
    assert bat_buoc + tu_chon == repo_all.curriculum(cur)["total_credits"]


@pytest.mark.parametrize("cur", CURRICULA)
def test_khoi_cha_bang_tong_khoi_con(blocks, cur):
    b = blocks[blocks["curriculum_code"] == cur]
    for _, cha in b[b["selection_rule"] == "container"].iterrows():
        con = b[(b["parent_block_id"] == cha["id"]) & (b["counts_toward_total"].astype(bool))]
        assert con["required_credits"].sum() == cha["required_credits"], f"{cur} khối {cha['code']}"


@pytest.mark.parametrize("cur", CURRICULA)
def test_khoi_bat_buoc_bang_tong_tin_chi_mon(repo_all, blocks, cur):
    c = repo_all.curriculum_courses(cur)
    b = blocks[(blocks["curriculum_code"] == cur) & (blocks["selection_rule"] == "all")]
    for _, k in b.iterrows():
        assert c[c["block_code"] == k["code"]]["credits"].sum() == k["required_credits"], f"{cur} khối {k['code']}"


@pytest.mark.parametrize("cur", CURRICULA)
def test_mon_chi_nam_o_khoi_la(repo_all, cur):
    assert (repo_all.curriculum_courses(cur)["selection_rule"] != "container").all()


@pytest.mark.parametrize("cur", CURRICULA)
def test_khoi_tu_chon_chon_duoc_dung_so_tin_chi(repo_all, cur):
    c = repo_all.curriculum_courses(cur)
    for b in repo_all.elective_blocks(cur).itertuples():
        tc = list(c[c["block_code"] == b.block_code]["credits"])
        ok = any(sum(x) == b.required_credits for k in range(1, len(tc) + 1) for x in combinations(tc, k))
        assert ok, f"{cur} khối {b.block_code}: không chọn được đúng {b.required_credits} tín chỉ"


@pytest.mark.parametrize("cur", CURRICULA)
def test_dieu_kien_tien_quyet(repo_all, cur):
    c = repo_all.curriculum_courses(cur).set_index("course_code")
    raw = repo_all._q("""SELECT course_code, group_no, MAX(in_curriculum) AS ok FROM v_prerequisites p
                         JOIN curricula cu ON cu.id = p.curriculum_id WHERE cu.code = :c
                         GROUP BY course_code, group_no""", c=cur)
    assert raw["ok"].all(), f"Điều kiện không thể thỏa: {raw[raw['ok'] == 0].values.tolist()}"
    for m, mon in c.iterrows():
        for g in mon["prerequisite_groups"]:
            assert min(c.loc[x, "recommended_semester"] for x in g) < mon["recommended_semester"], f"{m} cần {g}"

    def vong(m, path):
        return m in path or any(vong(x, path | {m}) for g in c.loc[m, "prerequisite_groups"] for x in g)
    assert not [m for m in c.index if vong(m, set())]


def test_gio_hoc_khop_tin_chi_tru_loi_da_ghi_nhan(repo_all):
    hp = repo_all._q("""SELECT u.code AS u, c.code, c.credits, c.lecture_hours + c.practice_hours + c.self_study_hours AS h
                        FROM courses c JOIN universities u ON u.id = c.university_id WHERE c.lecture_hours IS NOT NULL""")
    lech = {f"{r.u}:{r.code}" for r in hp.itertuples() if r.h != r.credits * 50}
    da_ghi = set(repo_all._q("SELECT entity_key FROM data_issues WHERE issue_type = 'hours_mismatch'")["entity_key"])
    assert lech == da_ghi


@pytest.mark.parametrize("cur", CURRICULA)
def test_moi_hoc_phan_co_chu_de_chinh_va_ky_nang(repo_all, cur):
    """Thiếu đặc trưng thì thuật toán không nối được điểm môn đã học với môn tự chọn liên quan."""
    c = repo_all.curriculum_courses(cur)
    assert c["primary_topic"].notna().all(), list(c.loc[c["primary_topic"].isna(), "course_code"])
    assert (c["skills"].str.len() > 0).all(), list(c.loc[c["skills"].str.len() == 0, "course_code"])


@pytest.mark.parametrize("cur", CURRICULA)
def test_moi_khoi_tu_chon_co_mon_thuoc_nhieu_chu_de_hoac_mot_lua_chon(repo_all, cur):
    """Khối tự chọn có từ 2 chủ đề trở lên thì điểm mạnh theo chủ đề mới giúp phân biệt được môn nên chọn."""
    c = repo_all.curriculum_courses(cur).dropna(subset=["elective_block"])
    so_chu_de = c.groupby("elective_block")["primary_topic"].nunique()
    assert (so_chu_de >= 1).all()
    assert (so_chu_de >= 2).sum() >= 1, f"{cur}: mọi khối tự chọn chỉ có một chủ đề"


def test_thang_diem_lien_tuc_va_khop_diem_dat(repo_all):
    g = repo_all._q("""SELECT s.code, s.pass_score, s.max_score, c.letter, c.min_score, c.max_score AS hi, c.is_pass
                       FROM grade_conversions c JOIN grading_schemes s ON s.id = c.grading_scheme_id""")
    for code, d in g.groupby("code"):
        d = d.sort_values("min_score")
        assert float(d["min_score"].iloc[0]) == 0 and float(d["hi"].iloc[-1]) == float(d["max_score"].iloc[0])
        assert ((d["min_score"].astype(float) >= float(d["pass_score"].iloc[0])) == d["is_pass"].astype(bool)).all(), code


@pytest.mark.parametrize("cur", CURRICULA)
def test_hoc_phan_cung_truong_voi_khung(repo_all, cur):
    r = repo_all._q("""SELECT DISTINCT cu.code, mu.code AS u1, cu2.code AS u2 FROM curriculum_courses cc
                       JOIN curricula cu ON cu.id = cc.curriculum_id JOIN majors m ON m.id = cu.major_id
                       JOIN universities mu ON mu.id = m.university_id JOIN courses c ON c.id = cc.course_id
                       JOIN universities cu2 ON cu2.id = c.university_id WHERE cu.code = :c""", c=cur)
    assert (r["u1"] == r["u2"]).all()
