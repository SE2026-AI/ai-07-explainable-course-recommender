"""Mô phỏng quá trình học của sinh viên trên một khung CTĐT bất kỳ.

Không viết cứng mã khối, mã học phần hay mã CTĐT nào: mọi luật đọc từ dữ liệu
(khối tự chọn, điều kiện tiên quyết, thang điểm, tín chỉ tối đa mỗi kỳ).
"""
import random
from itertools import combinations

# Giả định khi sinh dữ liệu (không phải quy định của trường)
PREFER_COURSE = {"FLF1107": 4.0}      # phần lớn sinh viên chọn Tiếng Anh B1
EXEMPT_RATE = {"FLF1107": 0.10}       # 10% sinh viên chọn Tiếng Anh được miễn nhờ chứng chỉ


def term_code(cohort, t):
    """Kỳ thứ t (1, 2, …) của khóa `cohort` -> mã học kỳ, ví dụ khóa 2024, t=3 -> '20251'."""
    return f"{cohort + (t - 1) // 2}{1 if t % 2 == 1 else 2}"


def satisfied(groups, passed):
    return all(any(m in passed for m in g) for g in groups)


class Curriculum:
    """Khung CTĐT ở dạng tiện mô phỏng (dict thường, không gọi pandas trong vòng lặp)."""

    def __init__(self, info, courses, blocks, conversions):
        self.code = info.name
        self.max_credits = int(info["max_credits_per_term"])
        self.pass_score = float(info["pass_score"])
        self.max_score = float(info["max_score"])
        self.semesters = int(info["standard_semesters"])
        self.cohort_from = int(info["effective_from_cohort"])
        c = courses.set_index("course_code")
        self.credits = c["credits"].astype(int).to_dict()
        self.semester = c["recommended_semester"].astype(int).to_dict()
        self.counts = c["counts_toward_total"].astype(int).to_dict()
        self.groups = c["prerequisite_groups"].to_dict()
        self.skills = c["skills"].to_dict()
        self.topic = c["primary_topic"].to_dict()
        self.required = set(c.index[c["is_required"] == 1])
        self.block_of = c["elective_block"].dropna().to_dict()
        self.blocks = list(blocks.itertuples())
        self.conversions = sorted(conversions, key=lambda x: -x["min_score"])

    def letter(self, score):
        for cv in self.conversions:
            if score >= cv["min_score"]:
                return cv["letter"], cv["grade_point"]
        return self.conversions[-1]["letter"], self.conversions[-1]["grade_point"]

    def choose_electives(self, preference, rng, noise=1.0):
        """Mỗi khối tự chọn: bộ môn có tổng tín chỉ ĐÚNG bằng số cần, học được, được sinh viên ưa nhất.

        preference: dict mã môn -> mức ưa (ví dụ từ điểm mạnh theo chủ đề và sở thích); môn thiếu = 0."""
        chosen = set()
        for b in self.blocks:
            ds = sorted(m for m, blk in self.block_of.items() if blk == b.block_code)
            score = {m: preference.get(m, 0.0) + PREFER_COURSE.get(m, 0) + rng.random() * noise for m in ds}
            best, best_score = None, None
            for k in range(1, b.required_credits // min(self.credits[m] for m in ds) + 1):
                for bo in combinations(ds, k):
                    if sum(self.credits[m] for m in bo) != b.required_credits:
                        continue
                    can = self.required | chosen | set(bo)
                    if not all(any(x in can for x in g) for m in bo for g in self.groups[m]):
                        continue
                    s = sum(score[m] for m in bo) / len(bo)
                    if best_score is None or s > best_score:
                        best, best_score = bo, s
            if best is None:
                raise ValueError(f"{self.code}: khối {b.block_code} không có bộ môn nào đủ đúng {b.required_credits} TC")
            chosen |= set(best)
        return chosen

    def plan(self, electives):
        return self.required | electives

    def pick_term(self, t, plan, passed, failed, rng, retake_p=0.7, defer_p=0.05):
        """Môn đăng ký ở kỳ thứ t."""
        cand = []
        for m in sorted(plan):                       # sắp xếp: kết quả không phụ thuộc thứ tự set
            if m in passed or not satisfied(self.groups[m], passed):
                continue
            if m in failed:
                if rng.random() < retake_p:
                    cand.append((0, self.semester[m], m))
            elif self.semester[m] <= t:
                if self.semester[m] == t and rng.random() < defer_p:
                    continue
                cand.append((1, self.semester[m], m))
        out, credits = [], 0
        for _, _, m in sorted(cand):
            if self.counts[m]:
                if credits + self.credits[m] > self.max_credits:
                    continue
                credits += self.credits[m]
            out.append(m)
        return out

    def simulate(self, plan, cohort, n_terms, score_fn, rng, exempt=(), retake_p=0.7, defer_p=0.05):
        """Trả về (danh sách kết quả, môn đã đạt, môn đang nợ)."""
        passed, failed, rows, attempts = set(exempt), set(), [], {}
        for m in sorted(exempt):
            rows.append({"course_code": m, "term_code": term_code(cohort, 1), "attempt_no": 1, "score": None,
                             "letter_grade": None, "grade_point": None, "status": "exempted"})
        for t in range(1, n_terms + 1):
            for m in self.pick_term(t, plan, passed, failed, rng, retake_p, defer_p):
                s = round(min(self.max_score, max(0.0, score_fn(m))), 1)
                attempts[m] = attempts.get(m, 0) + 1
                ok = s >= self.pass_score
                letter, gp = self.letter(s)
                rows.append({"course_code": m, "term_code": term_code(cohort, t), "attempt_no": attempts[m], "score": s,
                                 "letter_grade": letter, "grade_point": gp, "status": "passed" if ok else "failed"})
                if ok:
                    passed.add(m)
                    failed.discard(m)
                else:
                    failed.add(m)
        return rows, passed, failed

    def next_term(self, plan, n_terms_done, passed, failed):
        """Môn sẽ đăng ký ở kỳ tiếp theo nếu học đúng kế hoạch (đáp án để đo độ chính xác)."""
        return self.pick_term(n_terms_done + 1, plan, passed, failed, random.Random(0), retake_p=1.0, defer_p=0.0)

    def elective_topics(self, exclude=()):
        """Chủ đề có môn tự chọn trong khung (là chủ đề mà sở thích/điểm mạnh có thể ảnh hưởng tới lựa chọn)."""
        return sorted({self.topic[m] for m in self.block_of} - set(exclude))


def load_curriculum(repo, code):
    info = repo.curriculum(code)
    conv = repo._q("""SELECT gc.letter, gc.min_score, gc.grade_point FROM grade_conversions gc
                      JOIN curricula cu ON cu.grading_scheme_id = gc.grading_scheme_id WHERE cu.code = :c""", c=code)
    conv = [{"letter": r.letter, "min_score": float(r.min_score), "grade_point": float(r.grade_point)} for r in conv.itertuples()]
    return Curriculum(info, repo.curriculum_courses(code), repo.elective_blocks(code), conv)
