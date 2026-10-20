"""Lớp truy cập dữ liệu: trả về pandas DataFrame đơn giản cho thuật toán gợi ý.

Code của app chỉ gọi các hàm ở đây, không viết SQL rải rác.
Kết nối PostgreSQL lấy từ biến môi trường DATABASE_URL.

    from src.data.repository import Repository
    repo = Repository()                                   # đọc DATABASE_URL
    students = repo.students()
    courses = repo.curriculum_courses(students.iloc[0]["curriculum_code"])
"""
import pandas as pd
from sqlalchemy import text

from .db.build import get_engine


def _lists(df, key, col):
    return df.groupby(key)[col].apply(list).to_dict()


def _as_list(value):
    """Giá trị của cột list sau `map()`: khóa không có trong bảng tra cho NaN, đổi thành list rỗng."""
    return value if isinstance(value, list) else []


# Lần học gần nhất của mỗi môn, chỉ tính các học kỳ TRƯỚC :t (hợp đồng mục 3.1). Cùng thứ tự với view
# v_course_results: học kỳ mới nhất trước, rồi lần học sau cùng.
_LATEST_BEFORE_TERM = """
    SELECT student_id, course_id, course_code, term_code, attempt_no, score, letter_grade, grade_point, status
    FROM (SELECT r.student_id, r.course_id, c.code AS course_code, t.code AS term_code, r.attempt_no, r.score,
                 r.letter_grade, r.grade_point, r.status,
                 ROW_NUMBER() OVER (PARTITION BY r.student_id, r.course_id
                                    ORDER BY t.code DESC, r.attempt_no DESC) AS recency
          FROM course_results r JOIN courses c ON c.id = r.course_id JOIN terms t ON t.id = r.term_id
          WHERE r.student_id = :s AND t.code < :t) ranked
    WHERE recency = 1"""

# Tín chỉ và GPA của CTĐT chính: CÙNG công thức với view v_student_progress, nhưng chỉ tính các học kỳ
# TRƯỚC :t. View không nhận tham số nên phải chép; test_repository kiểm hai bản cho cùng kết quả.
_PROGRESS_BEFORE_TERM = f"""
    WITH latest AS ({_LATEST_BEFORE_TERM})
    SELECT sp.student_id,
           COALESCE(SUM(c.credits) FILTER (WHERE l.status IN ('passed', 'exempted') AND b.counts_toward_total), 0)
               AS credits_earned,
           COALESCE(SUM(c.credits) FILTER (WHERE l.status = 'failed' AND b.counts_toward_total), 0)
               AS credits_outstanding,
           ROUND(SUM(l.grade_point * c.credits) FILTER (WHERE l.status IN ('passed', 'failed') AND b.counts_toward_total)
                 / NULLIF(SUM(c.credits) FILTER (WHERE l.status IN ('passed', 'failed') AND b.counts_toward_total), 0), 2)
               AS gpa
    FROM student_programs sp
    LEFT JOIN latest l ON l.student_id = sp.student_id
    LEFT JOIN courses c ON c.id = l.course_id
    LEFT JOIN curriculum_courses cc ON cc.curriculum_id = sp.curriculum_id AND cc.course_id = l.course_id
    LEFT JOIN curriculum_blocks b ON b.id = cc.block_id
    WHERE sp.student_id = :s AND sp.is_primary
    GROUP BY sp.student_id"""


def _attempt(row):
    """Một lần học, đúng dạng `last_attempt` của hợp đồng mục 6.5, thêm `status` của lần học đó."""
    return {"term_code": str(row.term_code), "attempt_no": int(row.attempt_no),
            "score": None if pd.isna(row.score) else float(row.score),
            "letter_grade": None if pd.isna(row.letter_grade) else str(row.letter_grade),
            "status": str(row.status)}


def _add_result_columns(students, latest):
    """Thêm `passed_courses`, `outstanding_courses`, `latest_scores`, `latest_attempts` từ `latest` — lần học
    gần nhất của mỗi cặp sinh viên, môn.

    Dùng chung cho `students()` và `student()`, nên hai hàm không thể tính lệch nhau. Danh sách sắp theo mã
    môn để phản hồi tất định (hợp đồng mục 1, nguyên tắc 7)."""
    latest = latest.sort_values(["student_id", "course_code"])
    passed = latest[latest["status"].isin(["passed", "exempted"])]
    failed = latest[latest["status"] == "failed"]
    students["passed_courses"] = students["student_id"].map(_lists(passed, "student_id", "course_code")).apply(_as_list)
    students["outstanding_courses"] = students["student_id"].map(_lists(failed, "student_id", "course_code")).apply(_as_list)
    scores, attempts = {}, {}
    for row in latest.itertuples():
        attempts.setdefault(row.student_id, {})[row.course_code] = _attempt(row)
        if not pd.isna(row.score):
            scores.setdefault(row.student_id, {})[row.course_code] = float(row.score)
    students["latest_scores"] = students["student_id"].map(lambda sid: scores.get(sid, {}))
    students["latest_attempts"] = students["student_id"].map(lambda sid: attempts.get(sid, {}))
    return students


class Repository:
    def __init__(self, url=None, engine=None):
        self.engine = engine or get_engine(url)

    def _q(self, sql, **params):
        with self.engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)

    # ---------------- Cấu hình, lịch ----------------
    def setting(self, key):
        return self._q("SELECT value FROM app_settings WHERE key = :k", k=key)["value"].iloc[0]

    def universities(self):
        """Danh sách trường. `is_demo` = 1 là trường giả lập chỉ dùng cho kiểm thử."""
        return self._q("""SELECT code AS university_code, name, name_en, short_name,
                                 CASE WHEN is_demo THEN 1 ELSE 0 END AS is_demo
                          FROM universities ORDER BY code""")

    def terms(self, university_code):
        """Lịch học kỳ của một trường, cũ đến mới. Mỗi trường có lịch riêng."""
        return self._q("""SELECT t.code AS term_code, t.term_no, t.name,
                                 a.code AS academic_year_code, a.start_year, t.start_date, t.end_date
                          FROM terms t JOIN universities u ON u.id = t.university_id
                          JOIN academic_years a ON a.id = t.academic_year_id
                          WHERE u.code = :u ORDER BY t.code""", u=university_code)

    def term(self, university_code, term_code):
        """Một học kỳ trong lịch của chính trường đó; `KeyError` khi trường không có học kỳ này.

        Mỗi trường có lịch riêng, nên một mã hợp lệ ở trường này có thể không tồn tại ở trường khác
        (hợp đồng mục 3.1). Tầng API dùng hàm này để trả `term_not_found`."""
        df = self._q("""SELECT t.id AS term_id, t.code AS term_code, t.term_no, a.start_year, t.name
                          FROM terms t JOIN universities u ON u.id = t.university_id
                          JOIN academic_years a ON a.id = t.academic_year_id
                          WHERE u.code = :u AND t.code = :c""", u=university_code, c=str(term_code))
        if df.empty:
            raise KeyError(f"Trường {university_code} chưa có học kỳ {term_code} trong bảng terms")
        return df.iloc[0]

    def target_term(self, university_code):
        """Học kỳ cần gợi ý (app_settings.target_term_code) trong lịch của chính trường đó."""
        return self.term(university_code, self.setting("target_term_code"))

    # ---------------- Chương trình đào tạo ----------------
    def curricula(self):
        return self._q("""SELECT cu.id AS curriculum_id, cu.code AS curriculum_code, u.code AS university_code,
                                 m.code AS major_code, m.name AS major_name, cu.name, cu.total_credits,
                                 cu.standard_semesters, cu.max_credits_per_term, g.pass_score, g.max_score,
                                 cu.effective_from_cohort, cu.effective_to_cohort, cu.status
                          FROM curricula cu JOIN majors m ON m.id = cu.major_id
                          JOIN universities u ON u.id = m.university_id
                          JOIN grading_schemes g ON g.id = cu.grading_scheme_id ORDER BY cu.code""")

    def curriculum(self, curriculum_code):
        return self.curricula().set_index("curriculum_code").loc[curriculum_code]

    def curriculum_courses(self, curriculum_code):
        """Mỗi dòng một học phần của khung. Cột list: skills, topics, prerequisite_groups.
        prerequisite_groups chỉ chứa mã THUỘC khung (mã ngành khác đã bỏ)."""
        df = self._q("SELECT * FROM v_curriculum_courses WHERE curriculum_code = :c ORDER BY sort_no", c=curriculum_code)
        ids = tuple(df["course_id"])
        sk = self._q("""SELECT cs.course_id, s.code FROM course_skills cs JOIN skills s ON s.id = cs.skill_id""")
        tp = self._q("""SELECT ct.course_id, t.code, ct.is_primary FROM course_topics ct JOIN topics t ON t.id = ct.topic_id""")
        pr = self._q("""SELECT course_code, group_no, required_course_code FROM v_prerequisites p
                        JOIN curricula c ON c.id = p.curriculum_id
                        WHERE c.code = :c AND in_curriculum = 1 ORDER BY group_no""", c=curriculum_code)
        sk, tp = sk[sk["course_id"].isin(ids)], tp[tp["course_id"].isin(ids)]
        df["skills"] = df["course_id"].map(_lists(sk, "course_id", "code")).apply(_as_list)
        df["topics"] = df["course_id"].map(_lists(tp, "course_id", "code")).apply(_as_list)
        chinh = tp[tp["is_primary"].astype(bool)].set_index("course_id")["code"]
        df["primary_topic"] = df["course_id"].map(chinh)
        nhom = pr.groupby(["course_code", "group_no"])["required_course_code"].apply(list)
        groups = nhom.groupby(level=0).apply(list).to_dict()
        df["prerequisite_groups"] = df["course_code"].map(groups).apply(_as_list)
        df["elective_block"] = df["block_code"].where(df["selection_rule"] == "choose_credits")
        return df

    def blocks(self, curriculum_code):
        """MỌI khối kiến thức của khung, dạng cây trả về phẳng kèm parent_block_code (None ở gốc).

        Khác `elective_blocks`: hàm này giữ cả khối `all` và khối `container`, nên dùng được để
        dựng cây khối và tính tiến độ. `counts_toward_total` = 0 là khối không tính vào tổng tín
        chỉ tốt nghiệp."""
        return self._q("""SELECT b.code AS block_code, b.name AS block_name,
                                 p.code AS parent_block_code, b.selection_rule, b.required_credits,
                                 CASE WHEN b.counts_toward_total THEN 1 ELSE 0 END AS counts_toward_total,
                                 b.sort_order, b.note
                          FROM curriculum_blocks b
                          JOIN curricula c ON c.id = b.curriculum_id
                          LEFT JOIN curriculum_blocks p ON p.id = b.parent_block_id
                          WHERE c.code = :c ORDER BY b.sort_order""", c=curriculum_code)

    def elective_blocks(self, curriculum_code):
        return self._q("""SELECT b.code AS block_code, b.name AS block_name, b.required_credits
                          FROM curriculum_blocks b JOIN curricula c ON c.id = b.curriculum_id
                          WHERE c.code = :c AND b.selection_rule = 'choose_credits' ORDER BY b.sort_order""",
                       c=curriculum_code)

    def topics(self):
        """Danh sách chủ đề học phần: `topic_code` và `topic_name`.

        `curriculum_courses()` chỉ trả về mã chủ đề; hàm này cho tên để hiện cho người dùng."""
        return self._q("SELECT code AS topic_code, name AS topic_name FROM topics ORDER BY code")

    # ---------------- Sinh viên ----------------
    def students(self, only_primary=True):
        """Mỗi dòng một sinh viên (CTĐT chính). KHÔNG chứa thuộc tính nhạy cảm.
        Cột tính sẵn: year_of_study, credits_earned, credits_outstanding, gpa (thang 4, NaN nếu chưa có điểm),
        passed_courses (list, gồm cả miễn), outstanding_courses (list môn trượt chưa học lại đạt),
        latest_scores (dict mã môn -> điểm lần gần nhất), latest_attempts (dict mã môn -> lần học gần nhất),
        interests (list chủ đề tự khai, mạnh nhất trước – tín hiệu phụ).

        Đọc cả trường mỗi lần gọi: endpoint của MỘT sinh viên dùng `student()`."""
        sv = self._q("SELECT * FROM v_student_programs" + (" WHERE is_primary" if only_primary else ""))
        if sv.empty:
            return sv
        nam = {u: int(self.target_term(u)["start_year"]) for u in sv["university_code"].unique()}
        sv["year_of_study"] = sv["university_code"].map(nam) - sv["cohort_year"] + 1
        tien_do = self._q("SELECT student_id, credits_earned, credits_outstanding, gpa FROM v_student_progress")
        sv = sv.merge(tien_do, on="student_id", how="left")
        sv["gpa"] = sv["gpa"].astype(float)
        it = self._q("""SELECT i.student_id, t.code FROM student_interests i JOIN topics t ON t.id = i.topic_id
                        ORDER BY i.student_id, i.weight DESC, t.code""")
        sv["interests"] = sv["student_id"].map(_lists(it, "student_id", "code")).apply(_as_list)
        return _add_result_columns(sv, self._q("SELECT * FROM v_course_results WHERE recency = 1"))

    def student(self, university_code, student_code, term_code=None):
        """Một sinh viên theo CTĐT chính, nhìn từ đầu học kỳ `term_code` (mặc định: học kỳ cần gợi ý).

        Cùng tập cột với một dòng của `students()`, nhưng mọi thứ suy ra từ kết quả học tập — môn đã đạt,
        môn đang nợ, điểm, lần học gần nhất, tín chỉ, GPA — chỉ tính trên các học kỳ TRƯỚC `term_code`, và
        `year_of_study` tính theo năm học của chính học kỳ đó (hợp đồng mục 3.1). Ở học kỳ cần gợi ý, kết quả
        trùng `students()`.

        `None` khi trường không có sinh viên này với một CTĐT chính; `student_programs()` cho biết sinh viên
        có tồn tại hay không. Học kỳ không có trong lịch của trường thì `KeyError`, như `term()`."""
        term = self.term(university_code, term_code or self.setting("target_term_code"))
        row = self._q("""SELECT * FROM v_student_programs
                         WHERE university_code = :u AND student_code = :s AND is_primary""",
                      u=university_code, s=str(student_code))
        if row.empty:
            return None
        sid, code = int(row.iloc[0]["student_id"]), str(term["term_code"])
        row["year_of_study"] = int(term["start_year"]) - row["cohort_year"] + 1
        row = row.merge(self._q(_PROGRESS_BEFORE_TERM, s=sid, t=code), on="student_id", how="left")
        row["gpa"] = row["gpa"].astype(float)
        interests = self._q("""SELECT i.student_id, t.code FROM student_interests i JOIN topics t ON t.id = i.topic_id
                               WHERE i.student_id = :s ORDER BY i.weight DESC, t.code""", s=sid)
        row["interests"] = row["student_id"].map(_lists(interests, "student_id", "code")).apply(_as_list)
        return _add_result_columns(row, self._q(_LATEST_BEFORE_TERM, s=sid, t=code)).iloc[0]

    def student_programs(self, university_code, student_code):
        """Mọi CTĐT của một sinh viên, kể cả CTĐT phụ; rỗng khi trường không có sinh viên này.

        Cho tầng API phân biệt hai lỗi của mục 5: rỗng là `student_not_found`; có dòng nhưng không dòng nào
        vừa `is_primary` vừa `status = 'active'` là `no_primary_program`."""
        return self._q("""SELECT student_code, curriculum_code, cohort_year, status, is_primary
                          FROM v_student_programs WHERE university_code = :u AND student_code = :s
                          ORDER BY is_primary DESC, curriculum_code""", u=university_code, s=str(student_code))

    def block_progress(self, student_id, term_code=None):
        """Tiến độ theo từng khối của CTĐT chính: cần bao nhiêu tín chỉ, đã đạt bao nhiêu.

        Tính trên lần học gần nhất của mỗi môn, chỉ các học kỳ TRƯỚC `term_code` (mặc định: học kỳ cần gợi
        ý), cùng mốc với `student()`; môn được miễn tính là đạt. Khối `container` luôn có earned_credits = 0
        vì không chứa học phần trực tiếp."""
        return self._q(f"""WITH latest AS ({_LATEST_BEFORE_TERM})
                          SELECT b.code AS block_code, b.name AS block_name, b.selection_rule,
                                 b.required_credits,
                                 CASE WHEN b.counts_toward_total THEN 1 ELSE 0 END AS counts_toward_total,
                                 COALESCE(SUM(c.credits) FILTER (
                                     WHERE r.status IN ('passed', 'exempted')), 0) AS earned_credits
                          FROM student_programs sp
                          JOIN curriculum_blocks b ON b.curriculum_id = sp.curriculum_id
                          LEFT JOIN curriculum_courses cc ON cc.block_id = b.id
                          LEFT JOIN courses c ON c.id = cc.course_id
                          LEFT JOIN latest r ON r.course_id = cc.course_id
                          WHERE sp.student_id = :s AND sp.is_primary
                          GROUP BY b.id, b.code, b.name, b.selection_rule, b.required_credits,
                                   b.counts_toward_total, b.sort_order
                          ORDER BY b.sort_order""",
                       s=student_id, t=str(term_code or self.setting("target_term_code")))

    def student_interests(self, student_id=None):
        """Chủ đề sinh viên tự khai, mạnh nhất trước, kèm tên chủ đề và trọng số (0 < weight <= 1).

        Khác cột `interests` của `students()`: cột đó chỉ có mã chủ đề, hàm này có cả trọng số nên
        tầng xếp hạng tính được `contribution` của tiêu chí `interest`. Đây là tín hiệu PHỤ."""
        sql = """SELECT i.student_id, t.code AS topic_code, t.name AS topic_name, i.weight
                 FROM student_interests i JOIN topics t ON t.id = i.topic_id"""
        sql += " WHERE i.student_id = :s" if student_id else ""
        df = self._q(sql + " ORDER BY i.student_id, i.weight DESC, t.code", s=student_id)
        df["weight"] = df["weight"].astype(float)
        return df

    def course_results(self, student_id=None):
        sql = "SELECT * FROM v_course_results" + (" WHERE student_id = :s" if student_id else "")
        return self._q(sql + " ORDER BY student_id, term_code, course_code", s=student_id)

    def registrations(self, term_code=None):
        return self._q("""SELECT r.student_id, c.code AS course_code, t.code AS term_code, r.status, r.source
                          FROM course_registrations r JOIN courses c ON c.id = r.course_id
                          JOIN terms t ON t.id = r.term_id""" + (" WHERE t.code = :t" if term_code else ""), t=term_code)

    def sensitive_attributes(self):
        """CHỈ dùng cho đánh giá công bằng. Không đưa vào thuật toán gợi ý."""
        return self._q("SELECT student_id, attribute_code, value FROM student_attributes")

    # ---------------- Chất lượng dữ liệu ----------------
    def data_issues(self):
        """Các chỗ văn bản gốc mâu thuẫn hoặc thiếu, kèm văn bản đã dẫn ra chúng.

        Ghi lại thay vì âm thầm sửa, nên đây là dữ liệu công khai: `GET /v1/data-issues`."""
        return self._q("""SELECT s.code AS source_code, s.title AS source_title, s.document_number,
                                 i.entity_type, i.entity_key, i.issue_type, i.description, i.status
                          FROM data_issues i JOIN data_sources s ON s.id = i.source_id
                          ORDER BY s.code, i.entity_type, i.entity_key, i.issue_type""")
