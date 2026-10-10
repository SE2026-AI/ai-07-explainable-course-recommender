"""Tạo bộ sinh viên kiểm thử cố định và trạng thái mong đợi của từng học phần.

Chạy: python -m tools.generate_fixtures
Đọc: data/seed + test/fixtures/seed_demo (trường giả lập DEMO), nạp vào database PostgreSQL tạm
Ghi: test/fixtures/students/*.csv, gồm expected_course_status.csv và cases.csv

Điểm mặc định 7,5. Môn tự chọn chọn tự động theo chủ đề sinh viên thích (`interests`) hoặc chủ đề sinh viên
học giỏi (`strong`), trừ khi `force` ép chọn. Với `strong`, môn thuộc chủ đề đó được 9,0, môn khác 6,5.
"""
import os
import random

import pandas as pd

from src.data.db.build import scratch_build
from src.data.repository import Repository
from src.data.synthetic import load_curriculum

OUT = "test/fixtures/students"
KHMT, KHDL, DEMO = "HUS-7480113QTD-2022", "HUS-7460108-2022", "DEMO-7480201-2024"

CASES = [
 {"u": "HUS", "code": "T01", "cur": KHMT, "year": 1, "interests": ["tri_tue_nhan_tao"], "group": "A",
      "desc": "KHMT&TT năm 1, chưa học môn nào"},
 {"u": "HUS", "code": "T02", "cur": KHMT, "year": 2, "interests": ["phan_mem", "lap_trinh"], "group": "A",
      "desc": "KHMT&TT năm 2, đạt hết"},
 {"u": "HUS", "code": "T03", "cur": KHMT, "year": 2, "interests": ["phan_mem"], "group": "B",
      "scores": {"MAT2505": [3.0]}, "desc": "Trượt MAT2505 (3,0) kỳ 2, chưa học lại"},
 {"u": "HUS", "code": "T04", "cur": KHMT, "year": 3, "interests": ["phan_mem"], "group": "A",
      "scores": {"MAT2505": [3.5, 6.0]}, "desc": "Trượt MAT2505 kỳ 2, học lại đạt kỳ 3"},
 {"u": "HUS", "code": "T05", "cur": KHMT, "year": 2, "interests": ["du_lieu"], "group": "B",
      "scores": {"MAT2502": [4.0]}, "desc": "MAT2502 đúng 4,0 = đạt (ranh giới)"},
 {"u": "HUS", "code": "T06", "cur": KHMT, "year": 4, "interests": ["tri_tue_nhan_tao"], "group": "A",
      "desc": "KHMT&TT năm 4, còn rất ít môn"},
 {"u": "HUS", "code": "T07", "cur": KHMT, "year": 2, "interests": [], "group": "B",
      "desc": "Không có sở thích"},
 {"u": "HUS", "code": "T08", "cur": KHMT, "year": 2, "interests": ["phan_mem", "lap_trinh"], "group": "B",
      "copy_of": "T02", "desc": "Giống hệt T02, chỉ khác nhóm: gợi ý phải giống T02"},
 {"u": "HUS", "code": "T09", "cur": KHMT, "year": 3, "interests": ["phan_mem"], "group": "A",
      "force": {"I.2": ["FLF1207"]}, "desc": "Chọn Tiếng Nga B1; MAT1205E vẫn yêu cầu FLF1107"},
 {"u": "HUS", "code": "T10", "cur": KHMT, "year": 3, "interests": ["du_lieu"], "group": "B",
      "desc": "Đã đủ 5 TC khối lĩnh vực (II)"},
 {"u": "HUS", "code": "T11", "cur": KHDL, "year": 2, "interests": ["du_lieu"], "group": "A",
      "desc": "KHDL năm 2: dùng khung KHDL, không có MAT1205E"},
 {"u": "HUS", "code": "T12", "cur": KHDL, "year": 3, "interests": ["phan_mem", "du_lieu"], "group": "B",
      "desc": "KHDL năm 3: MAT3148 là môn bắt buộc, đã học kỳ 4"},
 {"u": "HUS", "code": "T13", "cur": KHDL, "year": 4, "interests": ["tri_tue_nhan_tao"], "group": "A",
      "desc": "KHDL năm 4: MAT3562 cần MAT2400 và MAT3533"},
 {"u": "HUS", "code": "T14", "cur": KHDL, "year": 3, "interests": ["du_lieu"], "group": "B",
      "scores": {"MAT2323": [3.0]}, "retake": False, "desc": "KHDL: trượt MAT2323 kỳ 3, chưa học lại"},
 {"u": "HUS", "code": "T15", "cur": KHMT, "year": 3, "interests": ["phan_mem"], "group": "A",
      "exempt": ["FLF1107"], "desc": "Miễn FLF1107 nhờ chứng chỉ: miễn tính là đạt, nên đã học được MAT1205E"},
 {"u": "DEMO", "code": "T01", "cur": DEMO, "year": 2, "interests": ["lap_trinh"], "group": "A",
      "scores": {"CS101": [4.5]}, "retake": False,
      "desc": "Trường DEMO, CÙNG mã T01 với sinh viên HUS; 4,5 là TRƯỢT vì DEMO đạt từ 5,0; đã học CS202 nhờ điều kiện HOẶC (MAT2505)"},
 {"u": "DEMO", "code": "T02", "cur": DEMO, "year": 2, "interests": ["du_lieu"], "group": "B",
      "desc": "Trường DEMO năm 2, đạt hết"},
 {"u": "HUS", "code": "T16", "cur": KHMT, "year": 3, "interests": [], "group": "A", "strong": "du_lieu",
      "desc": "Không khai sở thích; điểm cao ở các môn chủ đề Dữ liệu (9,0), môn khác 6,5"},
 {"u": "HUS", "code": "T17", "cur": KHMT, "year": 3, "interests": [], "group": "B", "strong": "toan",
      "desc": "Như T16 nhưng học giỏi chủ đề Toán: gợi ý tự chọn nên khác T16"},
]


def expected(cu, passed, outstanding, last_score):
    """Trạng thái đúng của từng học phần: passed / block_complete / missing_prerequisite / retake / eligible."""
    done = {}
    for m in passed:
        if m in cu.block_of:
            done[cu.block_of[m]] = done.get(cu.block_of[m], 0) + cu.credits[m]
    need = {b.block_code: b.required_credits for b in cu.blocks}
    rows = []
    for m in sorted(cu.credits):
        missing = ["|".join(g) for g in cu.groups[m] if not any(x in passed for x in g)]
        blk = cu.block_of.get(m)
        if m in passed:
            st = "passed"
        elif blk and done.get(blk, 0) >= need[blk]:
            st = "block_complete"
        elif missing:
            st = "missing_prerequisite"
        elif m in outstanding:
            st = "retake"
        else:
            st = "eligible"
        rows.append({"course_code": m, "expected_status": st,
                         "missing_prerequisites": ";".join(missing) if st == "missing_prerequisite" else "",
                         "last_score": last_score.get(m, "") if st == "retake" else ""})
    return rows


def main():
    with scratch_build(["data/seed", "test/fixtures/seed_demo"]) as engine:
        generate(Repository(engine=engine))


def generate(repo):
    out = {k: [] for k in ["students", "programs", "attributes", "interests", "results",
                           "registrations", "expected", "cases"]}
    made = {}
    for c in CASES:
        cu = load_curriculum(repo, c["cur"])
        target = repo.target_term(c["u"])
        cohort = int(target["start_year"]) - c["year"] + 1
        n_terms = 2 * (c["year"] - 1)
        key = {"university_code": c["u"], "student_code": c["code"]}
        if "copy_of" in c:
            rows, passed, failed, plan = made[(c["u"], c["copy_of"])]
        else:
            liked = {c["strong"]} if "strong" in c else set(c["interests"])
            electives = cu.choose_electives({m: 1.0 for m in cu.block_of if cu.topic[m] in liked},
                                            random.Random(1), noise=0)
            for blk, forced in c.get("force", {}).items():
                electives = {m for m in electives if cu.block_of.get(m) != blk} | set(forced)
            plan = cu.plan(electives)
            custom = {k: list(v) for k, v in c.get("scores", {}).items()}

            def score(m, cu=cu, c=c, custom=custom):
                if custom.get(m):
                    return custom[m].pop(0)
                if "strong" in c:
                    return 9.0 if cu.topic[m] == c["strong"] else 6.5
                return 7.5
            rows, passed, failed = cu.simulate(plan, cohort, n_terms, score, random.Random(1),
                                               exempt=c.get("exempt", ()),
                                               retake_p=1.0 if c.get("retake", True) else 0.0, defer_p=0.0)
        made[(c["u"], c["code"])] = (rows, passed, failed, plan)
        last = {r["course_code"]: r["score"] for r in rows}
        out["students"].append(dict(key, full_name=f"Sinh viên test {c['u']} {c['code']}", date_of_birth="",
                                    email="", is_synthetic=1))
        out["programs"].append(dict(key, curriculum_code=c["cur"], cohort_year=cohort,
                                    admission_term_code=f"{cohort}1", status="active", is_primary=1))
        out["attributes"].append(dict(key, attribute_code="fairness_group", value=c["group"]))
        out["interests"] += [dict(key, topic_code=t, weight=1.0 if i == 0 else 0.5) for i, t in enumerate(c["interests"])]
        out["results"] += [dict(key, **r) for r in rows]
        out["registrations"] += [dict(key, course_code=m, term_code=target["term_code"], status="registered",
                                      source="simulated") for m in cu.next_term(plan, n_terms, passed, failed)]
        out["expected"] += [dict(key, curriculum_code=c["cur"], **r) for r in expected(cu, passed, failed, last)]
        out["cases"].append(dict(key, curriculum_code=c["cur"], year_of_study=c["year"], description=c["desc"]))
    os.makedirs(OUT, exist_ok=True)
    names = {"students": "students", "programs": "student_programs", "attributes": "student_attributes",
                 "interests": "student_interests", "results": "course_results",
                 "registrations": "course_registrations", "expected": "expected_course_status", "cases": "cases"}
    for k, f in names.items():
        df = pd.DataFrame(out[k])
        if k == "results":
            df = df[["university_code", "student_code", "course_code", "term_code", "attempt_no", "score",
                     "letter_grade", "grade_point", "status"]]
        df.to_csv(os.path.join(OUT, f + ".csv"), index=False, encoding="utf-8-sig")
    print(f"{len(CASES)} sinh viên test, {len(out['results'])} kết quả, {len(out['expected'])} trạng thái mong đợi")


if __name__ == "__main__":
    main()
