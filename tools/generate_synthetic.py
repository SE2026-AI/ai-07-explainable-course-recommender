"""Sinh sinh viên và kết quả học tập tự tạo cho mọi CTĐT đang áp dụng.

Chạy từ thư mục gốc:  python -m tools.generate_synthetic
Đọc dữ liệu tham chiếu từ data/seed (nạp vào một database PostgreSQL tạm, tự xóa sau khi chạy),
ghi CSV vào data/synthetic/. Cần DATABASE_URL trỏ tới máy chủ PostgreSQL (xem docs/setup.md).
Cùng HAT_GIONG thì lần nào chạy cũng ra file giống hệt.

Mô hình sinh (giả định của nhóm, ghi rõ để thuật toán gợi ý có tín hiệu thật để học):
- Mỗi sinh viên có NĂNG LỰC CHUNG và ĐIỂM MẠNH/YẾU THEO CHỦ ĐỀ (ẩn, không ghi ra CSV).
- Điểm một môn = năng lực chung + điểm mạnh ở chủ đề của môn + nhiễu.
  => Nhìn điểm các môn đã học là đoán được sinh viên mạnh chủ đề nào.
- Môn tự chọn: sinh viên nghiêng về chủ đề mình mạnh (trọng số W_STRENGTH) và chủ đề mình thích (W_INTEREST).
- Sở thích tự khai: phần lớn trùng chủ đề mạnh nhất, phần còn lại ngẫu nhiên; một số sinh viên không khai.
"""
import os
import random

import pandas as pd

from src.data.db.build import scratch_build
from src.data.repository import Repository
from src.data.synthetic import EXEMPT_RATE, load_curriculum

SEED_DIR, OUT_DIR = "data/seed", "data/synthetic"
STUDENTS_PER_CURRICULUM = 100
HAT_GIONG = 42

STRENGTH_SD = 0.9        # độ lệch điểm mạnh/yếu theo chủ đề (thang 10)
SCORE_NOISE_SD = 1.2     # nhiễu điểm từng lần học (thang 10)
W_STRENGTH = 1.5         # mức ảnh hưởng của điểm mạnh tới chọn môn tự chọn
W_INTEREST = 1.0         # mức ảnh hưởng của sở thích (tín hiệu phụ)
P_NO_INTEREST = 0.10     # tỷ lệ không khai sở thích
P_INTEREST_IS_STRENGTH = 0.75   # tỷ lệ sở thích chính trùng chủ đề mạnh nhất
NOT_AN_INTEREST = ("ngoai_ngu", "chinh_tri_xa_hoi", "khoa_hoc_chung")   # chủ đề chung, không khai là sở thích

LAST = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Ngô"]
MIDDLE = ["Văn", "Thị", "Minh", "Đức", "Thu", "Ngọc", "Quang", "Thanh"]
FIRST = ["An", "Bình", "Chi", "Dũng", "Giang", "Hà", "Hải", "Hiếu", "Hoa", "Huy",
         "Khoa", "Lan", "Linh", "Long", "Mai", "Minh", "Nam", "Phương", "Trang", "Vy"]


def save(df, name):
    df.to_csv(os.path.join(OUT_DIR, name), index=False, encoding="utf-8-sig")


def main():
    with scratch_build([SEED_DIR]) as engine:
        generate(Repository(engine=engine))


def make_interests(strength, candidates, rng):
    """Sở thích tự khai: {chủ đề: trọng số}. 1 = chính, 0,5 = phụ."""
    if rng.random() < P_NO_INTEREST:
        return {}
    if rng.random() < P_INTEREST_IS_STRENGTH:
        main_topic = max(candidates, key=lambda t: (strength[t], t))
    else:
        main_topic = rng.choice(candidates)
    interests = {main_topic: 1.0}
    for t in rng.sample(candidates, rng.randint(0, 2)):
        interests.setdefault(t, 0.5)
    return interests


def generate(repo):
    rng = random.Random(HAT_GIONG)
    out = {k: [] for k in ["students", "programs", "attributes", "interests", "results", "registrations"]}
    seq = {}
    for cur in repo.curricula().itertuples():
        if cur.status != "active":
            continue
        cu = load_curriculum(repo, cur.curriculum_code)
        target = repo.target_term(cur.university_code)
        years = cu.semesters // 2
        frame = sorted(i % years + 1 for i in range(STUDENTS_PER_CURRICULUM))     # chia đều theo năm học
        topics = sorted(set(cu.topic.values()))
        candidates = cu.elective_topics(exclude=NOT_AN_INTEREST)
        scale = cu.max_score / 10
        by_year = {}
        for year in frame:
            cohort = int(target["start_year"]) - year + 1
            if cohort < cu.cohort_from:
                continue
            seq[cohort] = seq.get(cohort, 0) + 1
            code = f"{cohort % 100:02d}00{seq[cohort]:04d}"            # dạng mã sinh viên 8 chữ số
            key = {"university_code": cur.university_code, "student_code": code}

            ability = rng.uniform(5.0, 9.0) * scale                              # năng lực chung (ẩn)
            strength = {t: rng.gauss(0, STRENGTH_SD) * scale for t in topics}    # mạnh/yếu theo chủ đề (ẩn)
            interests = make_interests(strength, candidates, rng)
            preference = {m: W_STRENGTH * strength[cu.topic[m]] / scale + W_INTEREST * interests.get(cu.topic[m], 0)
                          for m in cu.block_of}
            plan = cu.plan(cu.choose_electives(preference, rng))
            n_terms = 2 * (year - 1)
            exempt = [m for m, p in EXEMPT_RATE.items() if m in plan and n_terms > 0 and rng.random() < p]

            def score(m, cu=cu, ability=ability, strength=strength, scale=scale):
                return rng.gauss(ability + strength[cu.topic[m]], SCORE_NOISE_SD * scale)

            rows, passed, failed = cu.simulate(plan, cohort, n_terms, score, rng, exempt=exempt)

            out["students"].append(dict(key, full_name=f"{rng.choice(LAST)} {rng.choice(MIDDLE)} {rng.choice(FIRST)}",
                                        date_of_birth="", email="", is_synthetic=1))
            out["programs"].append(dict(key, curriculum_code=cur.curriculum_code, cohort_year=cohort,
                                        admission_term_code=f"{cohort}1", status="active", is_primary=1))
            by_year.setdefault(year, []).append((ability, key))
            out["interests"] += [dict(key, topic_code=t, weight=w)
                                 for t, w in sorted(interests.items(), key=lambda x: (-x[1], x[0]))]
            out["results"] += [dict(key, **r) for r in rows]
            out["registrations"] += [dict(key, course_code=m, term_code=target["term_code"], status="registered",
                                          source="simulated")
                                     for m in cu.next_term(plan, n_terms, passed, failed)]
        # Nhóm công bằng: trong mỗi năm học, xếp theo năng lực rồi chia A/B xen kẽ kiểu ABBA,
        # để hai nhóm có năng lực tương đương. Nhóm KHÔNG ảnh hưởng tới quá trình học.
        for k, (_, ds) in enumerate(sorted(by_year.items())):
            dau, sau = ("A", "B") if k % 2 == 0 else ("B", "A")     # đảo mẫu ở năm kế tiếp để tổng 50/50
            for j, (_, key) in enumerate(sorted(ds, key=lambda x: -x[0])):
                g = dau if (j % 4) in (0, 3) else sau
                out["attributes"] += [dict(key, attribute_code="fairness_group", value=g),
                                      dict(key, attribute_code="gender", value=rng.choice(["female", "male"]))]
    os.makedirs(OUT_DIR, exist_ok=True)
    save(pd.DataFrame(out["students"]), "students.csv")
    save(pd.DataFrame(out["programs"]), "student_programs.csv")
    save(pd.DataFrame(out["attributes"]), "student_attributes.csv")
    save(pd.DataFrame(out["interests"]), "student_interests.csv")
    res = pd.DataFrame(out["results"])
    res = res[["university_code", "student_code", "course_code", "term_code", "attempt_no", "score",
               "letter_grade", "grade_point", "status"]]
    save(res, "course_results.csv")
    save(pd.DataFrame(out["registrations"]), "course_registrations.csv")
    print(f"{len(out['students'])} sinh viên, {len(res)} kết quả học tập, {len(out['registrations'])} đăng ký dự kiến")


if __name__ == "__main__":
    main()
