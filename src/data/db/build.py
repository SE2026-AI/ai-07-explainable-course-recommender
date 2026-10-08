"""Tạo cơ sở dữ liệu và nạp dữ liệu từ các thư mục CSV.

CSV dùng KHÓA TỰ NHIÊN (mã) cho dễ đọc, dễ sửa; khi nạp, mã được đổi sang `id` của bảng đích.
Một thư mục có thể chỉ chứa một phần các file (ví dụ chỉ dữ liệu sinh viên).
Thứ tự nạp do LOAD_ORDER quyết định, nên dữ liệu nhiều thư mục ghép được với nhau.

Chỉ hỗ trợ PostgreSQL. Địa chỉ lấy từ biến môi trường DATABASE_URL (xem .env.example).
"""
import os
import uuid
from contextlib import contextmanager
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from .schema import metadata
from .views import VIEWS

LOAD_ORDER = [
    "data_sources.csv", "data_issues.csv", "universities.csv", "faculties.csv", "majors.csv",
    "grading_schemes.csv", "grade_conversions.csv", "curricula.csv", "curriculum_blocks.csv", "courses.csv",
    "curriculum_courses.csv", "prerequisites.csv", "course_equivalences.csv", "skills.csv", "topics.csv",
    "course_skills.csv", "course_topics.csv",
    "academic_years.csv", "terms.csv", "app_settings.csv",
    "students.csv", "student_programs.csv", "student_attributes.csv",
    "student_interests.csv", "course_results.csv", "course_registrations.csv",
]


DEFAULT_URL = "postgresql+psycopg://coursereco:coursereco@localhost:5432/course_recommender"


def database_url(url=None):
    """URL được dùng: tham số > DATABASE_URL > mặc định khớp build/deploy/docker-compose.yml."""
    return url or os.environ.get("DATABASE_URL") or DEFAULT_URL


def get_engine(url=None):
    engine = create_engine(database_url(url))
    if engine.dialect.name != "postgresql":
        raise ValueError(f"Dự án chỉ dùng PostgreSQL, nhận được {engine.dialect.name!r}. "
                         "DATABASE_URL phải có dạng postgresql+psycopg://user:pass@host:port/dbname")
    return engine


@contextmanager
def temporary_database(base_url=None, prefix="tmp_coursereco"):
    """Tạo một database tạm trên cùng máy chủ PostgreSQL rồi xóa khi xong.

    Dùng cho sinh dữ liệu và kiểm thử: không đụng vào database thật.
    Tài khoản trong URL cần quyền CREATEDB (tài khoản của docker-compose có sẵn).
        with temporary_database() as url:
            engine, _ = build(url, ["data/seed"])
            ...
            engine.dispose()
    """
    base = make_url(database_url(base_url))
    name = f"{prefix}_{uuid.uuid4().hex[:10]}"
    admin = create_engine(base, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        yield base.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


# Bảng đã bỏ ở các phiên bản lược đồ trước. Khi tạo lại (drop=True) xóa luôn để database cũ
# của từng thành viên không chặn việc xóa bảng hiện tại. Không bao giờ xóa bảng lạ ngoài danh sách này.
RETIRED_TABLES = ["student_career_goals", "major_careers", "career_skills", "careers"]     # bỏ ở 3.0.0


def create_schema(engine, drop=False):
    with engine.begin() as conn:
        for name in VIEWS:
            conn.execute(text(f"DROP VIEW IF EXISTS {name} CASCADE"))
        if drop:
            for name in RETIRED_TABLES:
                conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
    if drop:
        metadata.drop_all(engine)
    metadata.create_all(engine)
    with engine.begin() as conn:
        for name, sql in VIEWS.items():
            conn.execute(text(f"CREATE VIEW {name} AS {sql}"))


class _Ids:
    """Tra mã -> id, đọc lại từ cơ sở dữ liệu khi cần."""

    def __init__(self, conn):
        self.conn = conn

    def _q(self, sql, **kw):
        return {tuple(r[:-1]) if len(r) > 2 else r[0]: r[-1] for r in self.conn.execute(text(sql), kw).all()}

    def map(self, what):
        q = {
            "data_source": "SELECT code, id FROM data_sources",
            "university": "SELECT code, id FROM universities",
            "faculty": "SELECT u.code, f.code, f.id FROM faculties f JOIN universities u ON u.id = f.university_id",
            "major": "SELECT u.code, m.code, m.id FROM majors m JOIN universities u ON u.id = m.university_id",
            "grading_scheme": "SELECT code, id FROM grading_schemes",
            "curriculum": "SELECT code, id FROM curricula",
            "block": "SELECT c.code, b.code, b.id FROM curriculum_blocks b JOIN curricula c ON c.id = b.curriculum_id",
            "course": "SELECT u.code, c.code, c.id FROM courses c JOIN universities u ON u.id = c.university_id",
            "curriculum_course": """SELECT cu.code, c.code, cc.id FROM curriculum_courses cc
                                    JOIN curricula cu ON cu.id = cc.curriculum_id JOIN courses c ON c.id = cc.course_id""",
            "skill": "SELECT code, id FROM skills", "topic": "SELECT code, id FROM topics",
            "academic_year": "SELECT u.code, a.code, a.id FROM academic_years a JOIN universities u ON u.id = a.university_id",
            "term": "SELECT u.code, t.code, t.id FROM terms t JOIN universities u ON u.id = t.university_id",
            "student": "SELECT u.code, s.student_code, s.id FROM students s JOIN universities u ON u.id = s.university_id",
            "curriculum_university": """SELECT cu.code, u.code FROM curricula cu JOIN majors m ON m.id = cu.major_id
                                        JOIN universities u ON u.id = m.university_id""",
        }[what]
        return self._q(q)


def _need(mapping, key, what):
    if key not in mapping:
        raise KeyError(f"Không tìm thấy {what} {key!r}")
    return mapping[key]


def _opt(v):
    return None if v == "" or pd.isna(v) else v


def _date(v):
    return date.fromisoformat(v) if _opt(v) else None


def _rows(ids, name, df):
    """Đổi một file CSV (khóa tự nhiên) thành (tên bảng, danh sách dòng có id)."""
    m = ids.map
    if name == "data_sources.csv":
        return "data_sources", [{"code": r.code, "title": r.title, "document_number": _opt(r.document_number),
                                     "issued_date": _date(r.issued_date), "issuer": _opt(r.issuer),
                                     "file_name": _opt(r.file_name), "note": _opt(r.note)} for r in df.itertuples()]
    if name == "data_issues.csv":
        s = m("data_source")
        return "data_issues", [{"source_id": _need(s, r.source_code, "nguồn"), "entity_type": r.entity_type,
                                    "entity_key": r.entity_key, "issue_type": r.issue_type, "description": r.description,
                                    "status": r.status} for r in df.itertuples()]
    if name == "universities.csv":
        return "universities", [{"code": r.code, "name": r.name, "name_en": _opt(r.name_en), "short_name": _opt(r.short_name),
                                     "is_demo": bool(int(r.is_demo))} for r in df.itertuples()]
    if name == "faculties.csv":
        u = m("university")
        return "faculties", [{"university_id": _need(u, r.university_code, "trường"), "code": r.code, "name": r.name,
                                  "name_en": _opt(r.name_en)} for r in df.itertuples()]
    if name == "majors.csv":
        u, f = m("university"), m("faculty")
        return "majors", [{"university_id": _need(u, r.university_code, "trường"), "code": str(r.code), "name": r.name,
                               "name_en": _opt(r.name_en),
                               "faculty_id": f.get((r.university_code, r.faculty_code)) if _opt(r.faculty_code) else None,
                               "degree_level": r.degree_level, "is_pilot": bool(int(r.is_pilot))} for r in df.itertuples()]
    if name == "grading_schemes.csv":
        u, s = m("university"), m("data_source")
        return "grading_schemes", [{"university_id": _need(u, r.university_code, "trường"), "code": r.code, "name": r.name,
                                        "max_score": r.max_score, "pass_score": r.pass_score,
                                        "source_id": s.get(r.source_code)} for r in df.itertuples()]
    if name == "grade_conversions.csv":
        g = m("grading_scheme")
        return "grade_conversions", [{"grading_scheme_id": _need(g, r.scheme_code, "thang điểm"), "letter": r.letter,
                                          "min_score": r.min_score, "max_score": r.max_score, "grade_point": r.grade_point,
                                          "is_pass": bool(int(r.is_pass))} for r in df.itertuples()]
    if name == "curricula.csv":
        mj, g, s = m("major"), m("grading_scheme"), m("data_source")
        return "curricula", [{"code": r.code, "major_id": _need(mj, (r.university_code, str(r.major_code)), "ngành"),
                                  "name": r.name, "name_en": _opt(r.name_en), "program_type": r.program_type,
                                  "effective_from_cohort": int(r.effective_from_cohort),
                                  "effective_to_cohort": int(r.effective_to_cohort) if _opt(r.effective_to_cohort) else None,
                                  "total_credits": int(r.total_credits), "standard_semesters": int(r.standard_semesters),
                                  "max_credits_per_term": int(r.max_credits_per_term),
                                  "grading_scheme_id": _need(g, r.grading_scheme_code, "thang điểm"),
                                  "source_id": s.get(r.source_code), "status": r.status} for r in df.itertuples()]
    if name == "curriculum_blocks.csv":
        c = m("curriculum")
        return "curriculum_blocks", [{"curriculum_id": _need(c, r.curriculum_code, "CTĐT"), "code": r.code, "name": r.name,
                                          "selection_rule": r.selection_rule, "required_credits": int(r.required_credits),
                                          "counts_toward_total": bool(int(r.counts_toward_total)),
                                          "sort_order": int(r.sort_order), "note": _opt(r.note)} for r in df.itertuples()]
    if name == "courses.csv":
        u = m("university")
        num = lambda v: int(v) if _opt(v) is not None else None
        return "courses", [{"university_id": _need(u, r.university_code, "trường"), "code": r.code, "name": r.name,
                                "name_en": _opt(r.name_en), "credits": int(r.credits), "lecture_hours": num(r.lecture_hours),
                                "practice_hours": num(r.practice_hours), "self_study_hours": num(r.self_study_hours),
                                "teaching_language": r.teaching_language} for r in df.itertuples()]
    if name == "curriculum_courses.csv":
        c, b, co, s, cu = m("curriculum"), m("block"), m("course"), m("data_source"), m("curriculum_university")
        return "curriculum_courses", [{
            "curriculum_id": _need(c, r.curriculum_code, "CTĐT"),
            "block_id": _need(b, (r.curriculum_code, r.block_code), "khối"),
            "course_id": _need(co, (cu[r.curriculum_code], r.course_code), "học phần"),
            "sort_no": int(r.sort_no) if _opt(r.sort_no) else None,
            "recommended_semester": int(r.recommended_semester) if _opt(r.recommended_semester) else None,
            "recommended_semester_source_id": s.get(r.recommended_semester_source), "note": _opt(r.note)}
            for r in df.itertuples()]
    if name == "prerequisites.csv":
        cc, co, cu = m("curriculum_course"), m("course"), m("curriculum_university")
        return "prerequisites", [{
            "curriculum_course_id": _need(cc, (r.curriculum_code, r.course_code), "học phần trong khung"),
            "group_no": int(r.group_no), "required_course_code": r.required_course_code,
            "required_course_id": co.get((cu[r.curriculum_code], r.required_course_code)),
            "requirement_type": r.requirement_type} for r in df.itertuples()]
    if name == "course_equivalences.csv":
        co, s = m("course"), m("data_source")
        return "course_equivalences", [{"course_id": _need(co, (r.university_code, r.course_code), "học phần"),
                                            "equivalent_course_id": _need(co, (r.university_code, r.equivalent_course_code), "học phần"),
                                            "source_id": s.get(r.source_code), "note": _opt(r.note)} for r in df.itertuples()]
    if name in ("skills.csv", "topics.csv"):
        return name[:-4], [{"code": r.code, "name": r.name} for r in df.itertuples()]
    if name == "course_skills.csv":
        co, sk = m("course"), m("skill")
        return "course_skills", [{"course_id": _need(co, (r.university_code, r.course_code), "học phần"),
                                      "skill_id": _need(sk, r.skill_code, "kỹ năng"), "weight": r.weight} for r in df.itertuples()]
    if name == "course_topics.csv":
        co, tp = m("course"), m("topic")
        return "course_topics", [{"course_id": _need(co, (r.university_code, r.course_code), "học phần"),
                                      "topic_id": _need(tp, r.topic_code, "chủ đề"), "is_primary": bool(int(r.is_primary))}
                                 for r in df.itertuples()]
    if name == "academic_years.csv":
        u = m("university")
        return "academic_years", [{"university_id": _need(u, r.university_code, "trường"), "code": r.code,
                                       "start_year": int(r.start_year)} for r in df.itertuples()]
    if name == "terms.csv":
        u, a = m("university"), m("academic_year")
        return "terms", [{"university_id": _need(u, r.university_code, "trường"), "code": str(r.code),
                              "academic_year_id": _need(a, (r.university_code, r.academic_year_code), "năm học"),
                              "term_no": int(r.term_no), "name": r.name, "start_date": _date(r.start_date),
                              "end_date": _date(r.end_date)} for r in df.itertuples()]
    if name == "app_settings.csv":
        return "app_settings", [{"key": r.key, "value": str(r.value), "note": _opt(r.note)} for r in df.itertuples()]
    if name == "students.csv":
        u = m("university")
        return "students", [{"university_id": _need(u, r.university_code, "trường"), "student_code": str(r.student_code),
                                 "full_name": r.full_name, "date_of_birth": _date(r.date_of_birth), "email": _opt(r.email),
                                 "is_synthetic": bool(int(r.is_synthetic))} for r in df.itertuples()]
    st = m("student") if name.startswith(("student_", "course_r")) else None
    sid = lambda r: _need(st, (r.university_code, str(r.student_code)), "sinh viên")
    if name == "student_programs.csv":
        c, t, cu = m("curriculum"), m("term"), m("curriculum_university")
        return "student_programs", [{"student_id": sid(r), "curriculum_id": _need(c, r.curriculum_code, "CTĐT"),
                                         "cohort_year": int(r.cohort_year),
                                         "admission_term_id": _term(t, ids, r.university_code, r.admission_term_code),
                                         "status": r.status, "is_primary": bool(int(r.is_primary))} for r in df.itertuples()]
    if name == "student_attributes.csv":
        return "student_attributes", [{"student_id": sid(r), "attribute_code": r.attribute_code, "value": str(r.value)}
                                      for r in df.itertuples()]
    if name == "student_interests.csv":
        tp = m("topic")
        return "student_interests", [{"student_id": sid(r), "topic_id": _need(tp, r.topic_code, "chủ đề"),
                                          "weight": r.weight} for r in df.itertuples()]
    if name in ("course_results.csv", "course_registrations.csv"):
        co, t = m("course"), m("term")
        base = lambda r: {"student_id": sid(r), "course_id": _need(co, (r.university_code, r.course_code), "học phần"),
                              "term_id": _term(t, ids, r.university_code, r.term_code), "status": r.status}
        if name == "course_results.csv":
            return "course_results", [dict(base(r), attempt_no=int(r.attempt_no), score=_opt(r.score),
                                           letter_grade=_opt(r.letter_grade), grade_point=_opt(r.grade_point))
                                      for r in df.itertuples()]
        return "course_registrations", [dict(base(r), source=r.source) for r in df.itertuples()]
    raise ValueError(f"Không biết nạp file {name}")


def _term(terms_map, ids, university_code, term_code):
    """Học kỳ luôn tra trong lịch của chính trường đó."""
    if _opt(term_code) is None:
        return None
    return _need(terms_map, (university_code, str(term_code).strip()), "học kỳ")


def load_directory(engine, folder):
    """Nạp mọi file CSV có trong `folder` theo LOAD_ORDER. Trả về số dòng đã nạp theo bảng."""
    dem = {}
    with engine.begin() as conn:
        ids = _Ids(conn)
        for name in LOAD_ORDER:
            path = os.path.join(folder, name)
            if not os.path.exists(path):
                continue
            df = pd.read_csv(path, keep_default_na=False, dtype=str)
            table, rows = _rows(ids, name, df)
            if rows:
                conn.execute(metadata.tables[table].insert(), rows)
            dem[table] = len(rows)
            if name == "curriculum_blocks.csv":     # khối cha-con: nạp xong mới gán khối cha
                b = ids.map("block")
                for r in df.itertuples():
                    if _opt(r.parent_code):
                        conn.execute(text("UPDATE curriculum_blocks SET parent_block_id = :p WHERE id = :i"),
                                     {"p": _need(b, (r.curriculum_code, r.parent_code), "khối"),
                                      "i": b[(r.curriculum_code, r.code)]})
    return dem


@contextmanager
def scratch_build(folders, base_url=None):
    """Dựng một database PostgreSQL TẠM từ các thư mục CSV; tự xóa khi ra khỏi khối `with`."""
    with temporary_database(base_url) as url:
        engine, _ = build(url, folders)
        try:
            yield engine
        finally:
            engine.dispose()


def build(url, folders, drop=True):
    """Tạo lại toàn bộ cơ sở dữ liệu rồi nạp các thư mục CSV theo thứ tự."""
    engine = get_engine(url)
    create_schema(engine, drop=drop)
    tong = {}
    for f in folders:
        for k, v in load_directory(engine, f).items():
            tong[k] = tong.get(k, 0) + v
    return engine, tong
