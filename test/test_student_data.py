"""Dữ liệu sinh viên và kết quả học tập hợp lệ, trên cả dữ liệu tự tạo và sinh viên kiểm thử."""
import pytest

REPOS = ["repo", "repo_all"]


@pytest.fixture(params=REPOS)
def r(request):
    return request.getfixturevalue(request.param)


def _results(r):
    return r._q("""SELECT res.*, sp.curriculum_id, cu.code AS curriculum_code, sp.cohort_year, g.pass_score,
                          cu.max_credits_per_term, c.code AS course_code, c.credits, t.code AS term_code, u.code AS uni
                   FROM course_results res
                   JOIN student_programs sp ON sp.student_id = res.student_id AND sp.is_primary
                   JOIN curricula cu ON cu.id = sp.curriculum_id
                   JOIN grading_schemes g ON g.id = cu.grading_scheme_id
                   JOIN courses c ON c.id = res.course_id JOIN terms t ON t.id = res.term_id
                   JOIN students s ON s.id = res.student_id JOIN universities u ON u.id = s.university_id""")


def test_moi_sinh_vien_mot_ctdt_chinh_hop_le(r):
    sp = r._q("""SELECT sp.student_id, sp.cohort_year, cu.effective_from_cohort, cu.status
                 FROM student_programs sp JOIN curricula cu ON cu.id = sp.curriculum_id WHERE sp.is_primary""")
    assert sp["student_id"].is_unique
    assert len(sp) == len(r._q("SELECT id FROM students"))
    assert (sp["cohort_year"] >= sp["effective_from_cohort"]).all() and (sp["status"] == "active").all()


def test_so_thich_la_chu_de_co_trong_khung_va_toi_da_mot_so_thich_chinh(r):
    it = r._q("""SELECT i.student_id, t.code AS topic, i.weight, cu.code AS curriculum_code
                 FROM student_interests i JOIN topics t ON t.id = i.topic_id
                 JOIN student_programs sp ON sp.student_id = i.student_id AND sp.is_primary
                 JOIN curricula cu ON cu.id = sp.curriculum_id""")
    for cur, d in it.groupby("curriculum_code"):
        assert d["topic"].isin(set(r.curriculum_courses(cur)["primary_topic"])).all(), cur
    assert (it[it["weight"].astype(float) == 1].groupby("student_id").size() <= 1).all()


def test_tien_do_hoc_tap_hop_le(r):
    sv = r.students()
    tong = sv["curriculum_code"].map(r.curricula().set_index("curriculum_code")["total_credits"])
    assert ((sv["credits_earned"] >= 0) & (sv["credits_earned"] <= tong)).all()
    co_diem = sv["gpa"].notna()
    assert ((sv.loc[co_diem, "gpa"] >= 0) & (sv.loc[co_diem, "gpa"] <= 4)).all()
    assert (sv.loc[sv["latest_scores"].str.len() == 0, "credits_earned"] == 0).all()   # chưa học: 0 tín chỉ
    # tín chỉ nợ chỉ đếm môn tính vào tổng (HUS1012 Kỹ năng bổ trợ không tính)
    for cur, d in sv.groupby("curriculum_code"):
        tinh = r.curriculum_courses(cur).set_index("course_code")["counts_toward_total"]
        co_no = d["outstanding_courses"].apply(lambda ms, tinh=tinh: any(tinh[m] == 1 for m in ms))
        assert co_no.eq(d["credits_outstanding"] > 0).all(), cur


def test_tin_chi_tich_luy_tinh_dung(repo_all):
    sv = repo_all.students().set_index(["university_code", "student_code"])
    s = sv.loc[("HUS", "T02")]
    c = repo_all.curriculum_courses(s["curriculum_code"]).set_index("course_code")
    dem = c.loc[s["passed_courses"]]
    assert s["credits_earned"] == dem.loc[dem["counts_toward_total"] == 1, "credits"].sum()
    assert s["gpa"] == pytest.approx(3.0)          # mọi môn 7,5 điểm = B = 3,0


def test_du_lieu_tu_tao_co_tin_hieu_diem_manh(repo):
    """Mô hình sinh: sinh viên chọn môn tự chọn thuộc chủ đề mình học tốt.
    Kiểm tra trên dữ liệu: điểm các môn BẮT BUỘC cùng chủ đề với môn tự chọn đã học phải cao hơn
    điểm trung bình của chính sinh viên đó. Nếu bài này hỏng, thuật toán dựa trên điểm sẽ không có gì để học."""
    lech = []
    for cur, d in repo.students().groupby("curriculum_code"):
        c = repo.curriculum_courses(cur).set_index("course_code")
        bat_buoc = set(c.index[c["is_required"] == 1])
        for s in d.itertuples():
            diem = {m: x for m, x in s.latest_scores.items() if m in bat_buoc}
            if len(diem) < 10:
                continue
            tb = sum(diem.values()) / len(diem)
            for m in s.passed_courses:
                if not isinstance(c.loc[m, "elective_block"], str):
                    continue
                cung = [x for k, x in diem.items() if c.loc[k, "primary_topic"] == c.loc[m, "primary_topic"]]
                if cung:
                    lech.append(sum(cung) / len(cung) - tb)
    assert len(lech) > 100
    assert sum(lech) / len(lech) > 0.25


def test_ket_qua_thuoc_khung_va_dung_thang_diem(r):
    res = _results(r)
    for cur, d in res.groupby("curriculum_code"):
        assert d["course_code"].isin(r.curriculum_courses(cur)["course_code"]).all(), cur
    d = res[res["status"].isin(["passed", "failed"])]
    assert ((d["score"].astype(float) >= d["pass_score"].astype(float)) == (d["status"] == "passed")).all()
    assert res[res["status"] == "exempted"]["score"].isna().all()


def test_hoc_dung_thu_tu_va_khong_hoc_lai_mon_da_dat(r):
    res = _results(r).sort_values("term_code")
    cache = {}
    for sid, ls in res.groupby("student_id"):
        cur = ls["curriculum_code"].iloc[0]
        c = cache.setdefault(cur, r.curriculum_courses(cur).set_index("course_code"))
        for _, row in ls.iterrows():
            truoc = ls[(ls["term_code"] < row["term_code"]) | ((ls["term_code"] == row["term_code"]) & (ls["status"] == "exempted"))]
            dat = set(truoc[truoc["status"].isin(["passed", "exempted"])]["course_code"])
            if row["status"] != "exempted":
                for g in c.loc[row["course_code"], "prerequisite_groups"]:
                    assert any(x in dat for x in g), f"{sid} học {row['course_code']} khi chưa đạt {g}"
            assert row["course_code"] not in set(ls[(ls["term_code"] < row["term_code"]) &
                                                    ls["status"].isin(["passed", "exempted"])]["course_code"])
        for m, d in ls.groupby("course_code"):
            assert list(d["attempt_no"]) == list(range(1, len(d) + 1)), f"{sid} {m}: số lần học sai"


def test_thoi_gian_hoc_hop_le(r):
    res = _results(r)
    for uni, d in res.groupby("uni"):
        ky = r.target_term(uni)["term_code"]
        nonex = d[d["status"] != "exempted"]
        assert (nonex["term_code"] < ky).all(), uni
        assert (d["term_code"].str[:4].astype(int) >= d["cohort_year"]).all(), uni


def test_tin_chi_moi_ky_va_khoi_tu_chon(r):
    res = _results(r)
    tinh = r._q("""SELECT cc.curriculum_id, cc.course_id, b.counts_toward_total FROM curriculum_courses cc
                   JOIN curriculum_blocks b ON b.id = cc.block_id""")
    res = res.merge(tinh, on=["curriculum_id", "course_id"])
    counted = res[res["status"].isin(["passed", "failed"]) & res["counts_toward_total"].astype(bool)]
    tong = counted.groupby(["student_id", "term_code"]).agg(tc=("credits", "sum"), mx=("max_credits_per_term", "first"))
    assert (tong["tc"] <= tong["mx"]).all()
    sv = r.students()
    for cur, d in sv.groupby("curriculum_code"):
        c = r.curriculum_courses(cur).set_index("course_code")
        need = r.elective_blocks(cur).set_index("block_code")["required_credits"]
        for s in d.itertuples():
            done = {}
            for m in s.passed_courses:
                b = c.loc[m, "elective_block"]
                if isinstance(b, str):
                    done[b] = done.get(b, 0) + c.loc[m, "credits"]
            assert all(v <= need[b] for b, v in done.items()), f"{s.student_code} học vượt khối tự chọn"


def test_dang_ky_ky_toi_hop_le(r):
    reg = r._q("""SELECT reg.student_id, c.code AS course_code, t.code AS term_code, u.code AS uni
                  FROM course_registrations reg JOIN courses c ON c.id = reg.course_id
                  JOIN terms t ON t.id = reg.term_id JOIN students s ON s.id = reg.student_id
                  JOIN universities u ON u.id = s.university_id""")
    sv = r.students().set_index("student_id")
    for _, x in reg.iterrows():
        assert x["term_code"] == r.target_term(x["uni"])["term_code"]
        assert x["course_code"] not in sv.loc[x["student_id"], "passed_courses"]


def test_repository_khong_lo_thuoc_tinh_nhay_cam(r):
    cols = set(r.students().columns)
    assert not cols & {"fairness_group", "gender", "attribute_code", "value"}


def test_nhom_cong_bang_can_bang(repo):
    sv = repo.students().merge(repo.sensitive_attributes().query("attribute_code == 'fairness_group'"),
                               on="student_id")
    kq = repo._q("SELECT student_id, score FROM course_results WHERE score IS NOT NULL").merge(sv, on="student_id")
    for cur, d in sv.groupby("curriculum_code"):
        dem = d["value"].value_counts()
        assert abs(dem.get("A", 0) - dem.get("B", 0)) <= 2, cur
        tb = kq[kq["curriculum_code"] == cur].groupby("value")["score"].mean()
        assert abs(tb["A"] - tb["B"]) < 0.3, cur
