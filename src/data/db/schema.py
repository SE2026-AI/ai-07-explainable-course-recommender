"""Lược đồ cơ sở dữ liệu – nguồn sự thật duy nhất cho mọi bảng.

Viết bằng SQLAlchemy Core, chạy trên PostgreSQL (≥ 14; dự án dùng 16).
Dùng kiểu riêng của PostgreSQL: JSONB, TIMESTAMPTZ, chỉ mục duy nhất có điều kiện.
Tài liệu: docs/architecture/data-model.md.

Quy ước:
- Mọi bảng thực thể có khóa thay thế `id` (số nguyên tự tăng). Mã nghiệp vụ (`code`,
  `student_code`…) là khóa duy nhất trong phạm vi của nó, KHÔNG dùng làm khóa ngoại.
- Bảng liên kết nhiều-nhiều dùng khóa chính ghép.
- Tên bảng số nhiều, snake_case, tiếng Anh.
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

FALSE, TRUE = text("false"), text("true")

metadata = MetaData(naming_convention={
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})


def pk():
    return Column("id", Integer, Identity(), primary_key=True)


def fk(name, target, nullable=False, ondelete="RESTRICT", comment=None):
    return Column(name, Integer, ForeignKey(target, ondelete=ondelete), nullable=nullable, index=True, comment=comment)


def created_at():
    return Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())


# ======================= Nguồn dữ liệu =======================
data_sources = Table(
    "data_sources", metadata, pk(),
    Column("code", String(50), nullable=False, unique=True),
    Column("title", Text, nullable=False),
    Column("document_number", String(50)),
    Column("issued_date", Date),
    Column("issuer", Text),
    Column("file_name", Text),
    Column("note", Text),
    comment="Văn bản/nguồn mà dữ liệu được lấy ra; mọi dữ liệu tham chiếu đều truy được về đây")

data_issues = Table(
    "data_issues", metadata, pk(),
    fk("source_id", "data_sources.id"),
    Column("entity_type", String(50), nullable=False),
    Column("entity_key", String(100), nullable=False),
    Column("issue_type", String(50), nullable=False),
    Column("description", Text, nullable=False),
    Column("status", String(20), nullable=False),
    CheckConstraint("status IN ('open', 'resolved_in_data', 'closed')", name="status"),
    comment="Chỗ văn bản gốc mâu thuẫn hoặc thiếu; ghi lại thay vì âm thầm sửa")

# ======================= Tổ chức đào tạo =======================
universities = Table(
    "universities", metadata, pk(),
    Column("code", String(20), nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("name_en", Text),
    Column("short_name", String(50)),
    Column("is_demo", Boolean, nullable=False, server_default=FALSE),
    comment="Trường đại học. Mỗi trường độc lập: có ngành, học phần, thang điểm, lịch học kỳ riêng")

faculties = Table(
    "faculties", metadata, pk(),
    fk("university_id", "universities.id"),
    Column("code", String(20), nullable=False),
    Column("name", Text, nullable=False),
    Column("name_en", Text),
    UniqueConstraint("university_id", "code"))

majors = Table(
    "majors", metadata, pk(),
    fk("university_id", "universities.id"),
    fk("faculty_id", "faculties.id", nullable=True),
    Column("code", String(20), nullable=False, comment="Mã ngành theo Bộ GD&ĐT, ví dụ 7460108"),
    Column("name", Text, nullable=False),
    Column("name_en", Text),
    Column("degree_level", String(20), nullable=False),
    Column("is_pilot", Boolean, nullable=False, server_default=FALSE, comment="Ngành đào tạo thí điểm"),
    UniqueConstraint("university_id", "code"),
    CheckConstraint("degree_level IN ('bachelor', 'engineer', 'master', 'doctor')", name="degree_level"),
    comment="Ngành đào tạo của một trường")

grading_schemes = Table(
    "grading_schemes", metadata, pk(),
    fk("university_id", "universities.id"),
    Column("code", String(30), nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("max_score", Numeric(4, 2), nullable=False),
    Column("pass_score", Numeric(4, 2), nullable=False),
    fk("source_id", "data_sources.id", nullable=True),
    CheckConstraint("pass_score > 0 AND pass_score <= max_score", name="pass_score"))

grade_conversions = Table(
    "grade_conversions", metadata, pk(),
    fk("grading_scheme_id", "grading_schemes.id", ondelete="CASCADE"),
    Column("letter", String(3), nullable=False),
    Column("min_score", Numeric(4, 2), nullable=False),
    Column("max_score", Numeric(4, 2), nullable=False),
    Column("grade_point", Numeric(3, 2), nullable=False),
    Column("is_pass", Boolean, nullable=False),
    UniqueConstraint("grading_scheme_id", "letter"),
    CheckConstraint("min_score <= max_score", name="range"))

# ======================= Chương trình đào tạo =======================
curricula = Table(
    "curricula", metadata, pk(),
    Column("code", String(50), nullable=False, unique=True, comment="TRƯỜNG-MÃNGÀNH-KHÓA, ví dụ HUS-7460108-2022"),
    fk("major_id", "majors.id"),
    Column("name", Text, nullable=False),
    Column("name_en", Text),
    Column("program_type", String(30), nullable=False),
    Column("effective_from_cohort", Integer, nullable=False),
    Column("effective_to_cohort", Integer, comment="NULL = còn áp dụng"),
    Column("total_credits", Integer, nullable=False),
    Column("standard_semesters", Integer, nullable=False),
    Column("max_credits_per_term", Integer, nullable=False),
    fk("grading_scheme_id", "grading_schemes.id"),
    fk("source_id", "data_sources.id", nullable=True),
    Column("status", String(20), nullable=False),
    CheckConstraint("status IN ('draft', 'active', 'retired')", name="status"),
    CheckConstraint("total_credits > 0 AND standard_semesters > 0", name="positive"),
    CheckConstraint("effective_to_cohort IS NULL OR effective_to_cohort >= effective_from_cohort", name="cohort_range"),
    comment="Khung chương trình đào tạo: một phiên bản của một ngành, áp dụng cho một dải khóa")

curriculum_blocks = Table(
    "curriculum_blocks", metadata, pk(),
    fk("curriculum_id", "curricula.id", ondelete="CASCADE"),
    Column("code", String(20), nullable=False, comment="Số mục trong văn bản: I, II, V.2.1…"),
    fk("parent_block_id", "curriculum_blocks.id", nullable=True),
    Column("name", Text, nullable=False),
    Column("selection_rule", String(20), nullable=False,
           comment="all = học hết; choose_credits = chọn đủ required_credits; container = chỉ chứa khối con"),
    Column("required_credits", Integer, nullable=False),
    Column("counts_toward_total", Boolean, nullable=False, server_default=TRUE),
    Column("sort_order", Integer, nullable=False),
    Column("note", Text),
    UniqueConstraint("curriculum_id", "code"),
    CheckConstraint("selection_rule IN ('all', 'choose_credits', 'container')", name="selection_rule"),
    comment="Khối kiến thức (cây). Nhóm tự chọn là khối có selection_rule = choose_credits")

courses = Table(
    "courses", metadata, pk(),
    fk("university_id", "universities.id"),
    Column("code", String(20), nullable=False),
    Column("name", Text, nullable=False),
    Column("name_en", Text),
    Column("credits", Integer, nullable=False),
    Column("lecture_hours", Integer),
    Column("practice_hours", Integer),
    Column("self_study_hours", Integer),
    Column("teaching_language", String(5), nullable=False, server_default="vi"),
    UniqueConstraint("university_id", "code"),
    CheckConstraint("credits > 0", name="credits"),
    comment="Học phần của một trường, dùng chung cho mọi CTĐT của trường đó")

curriculum_courses = Table(
    "curriculum_courses", metadata, pk(),
    fk("curriculum_id", "curricula.id", ondelete="CASCADE"),
    fk("block_id", "curriculum_blocks.id"),
    fk("course_id", "courses.id"),
    Column("sort_no", Integer, comment="STT trong văn bản"),
    Column("recommended_semester", Integer, comment="Kỳ thứ mấy của CTĐT nên học"),
    fk("recommended_semester_source_id", "data_sources.id", nullable=True),
    Column("note", Text),
    UniqueConstraint("curriculum_id", "course_id"),
    CheckConstraint("recommended_semester IS NULL OR recommended_semester >= 1", name="semester"),
    comment="Học phần thuộc khung nào, nằm trong khối nào")

prerequisites = Table(
    "prerequisites", metadata, pk(),
    fk("curriculum_course_id", "curriculum_courses.id", ondelete="CASCADE"),
    Column("group_no", Integer, nullable=False,
           comment="Cùng group_no = HOẶC; khác group_no = VÀ"),
    Column("required_course_code", String(20), nullable=False, comment="Ghi nguyên văn từ văn bản"),
    fk("required_course_id", "courses.id", nullable=True),
    Column("requirement_type", String(20), nullable=False, server_default="prerequisite"),
    Column("min_score", Numeric(4, 2), comment="NULL = chỉ cần đạt"),
    UniqueConstraint("curriculum_course_id", "group_no", "required_course_code"),
    CheckConstraint("requirement_type IN ('prerequisite', 'prior', 'corequisite')", name="requirement_type"),
    comment="Điều kiện của học phần TRONG một CTĐT (mỗi văn bản tự quy định)")

course_equivalences = Table(
    "course_equivalences", metadata, pk(),
    fk("course_id", "courses.id"),
    fk("equivalent_course_id", "courses.id"),
    fk("source_id", "data_sources.id", nullable=True),
    Column("note", Text),
    UniqueConstraint("course_id", "equivalent_course_id"),
    CheckConstraint("course_id <> equivalent_course_id", name="not_self"),
    comment="Học phần tương đương/thay thế")

# ======================= Đặc trưng học phần (để nối điểm số với môn liên quan) =======================
skills = Table("skills", metadata, pk(), Column("code", String(50), nullable=False, unique=True),
               Column("name", Text, nullable=False),
               comment="Kỹ năng mà học phần rèn luyện (danh mục do nhóm tự gán)")
topics = Table("topics", metadata, pk(), Column("code", String(50), nullable=False, unique=True),
               Column("name", Text, nullable=False),
               comment="Chủ đề học phần; dùng để nhóm các môn liên quan và cho sinh viên khai sở thích")

course_skills = Table(
    "course_skills", metadata,
    Column("course_id", Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True, index=True),
    Column("weight", Numeric(4, 2), nullable=False, server_default="1"),
    CheckConstraint("weight > 0", name="weight"),
    comment="Học phần rèn kỹ năng nào, mức độ (weight)")
course_topics = Table(
    "course_topics", metadata,
    Column("course_id", Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id"), primary_key=True, index=True),
    Column("is_primary", Boolean, nullable=False, server_default=FALSE),
    comment="Học phần thuộc chủ đề nào; mỗi học phần có đúng một chủ đề chính")

# ======================= Lịch học =======================
academic_years = Table(
    "academic_years", metadata, pk(),
    fk("university_id", "universities.id"),
    Column("code", String(20), nullable=False),
    Column("start_year", Integer, nullable=False),
    UniqueConstraint("university_id", "code"))

terms = Table(
    "terms", metadata, pk(),
    fk("university_id", "universities.id", comment="Trường sở hữu lịch học kỳ"),
    fk("academic_year_id", "academic_years.id"),
    Column("code", String(10), nullable=False, comment="NNNNK: năm bắt đầu + kỳ (3 = hè)"),
    Column("term_no", Integer, nullable=False),
    Column("name", Text, nullable=False),
    Column("start_date", Date),
    Column("end_date", Date),
    UniqueConstraint("university_id", "code"),
    CheckConstraint("term_no IN (1, 2, 3)", name="term_no"))

app_settings = Table(
    "app_settings", metadata,
    Column("key", String(50), primary_key=True),
    Column("value", Text, nullable=False),
    Column("note", Text))

# ======================= Sinh viên =======================
students = Table(
    "students", metadata, pk(),
    fk("university_id", "universities.id"),
    Column("student_code", String(30), nullable=False, comment="Mã sinh viên do trường cấp; chỉ duy nhất trong trường"),
    Column("full_name", Text, nullable=False),
    Column("date_of_birth", Date),
    Column("email", Text),
    Column("is_synthetic", Boolean, nullable=False, server_default=FALSE),
    created_at(),
    UniqueConstraint("university_id", "student_code"),
    comment="Sinh viên. Khóa là id; (university_id, student_code) là khóa nghiệp vụ")

student_programs = Table(
    "student_programs", metadata, pk(),
    fk("student_id", "students.id", ondelete="CASCADE"),
    fk("curriculum_id", "curricula.id"),
    Column("cohort_year", Integer, nullable=False, comment="Khóa tuyển sinh"),
    fk("admission_term_id", "terms.id", nullable=True),
    Column("status", String(20), nullable=False),
    Column("is_primary", Boolean, nullable=False, server_default=TRUE),
    Column("start_date", Date),
    Column("end_date", Date),
    created_at(),
    UniqueConstraint("student_id", "curriculum_id"),
    CheckConstraint("status IN ('active', 'graduated', 'suspended', 'withdrawn', 'transferred')", name="status"),
    CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="date_range"),
    comment="Sinh viên theo học CTĐT nào (cho phép chuyển ngành, học song ngành)")

student_attributes = Table(
    "student_attributes", metadata,
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("attribute_code", String(30), primary_key=True),
    Column("value", Text, nullable=False),
    comment="DỮ LIỆU NHẠY CẢM, chỉ dùng để đánh giá công bằng; thuật toán gợi ý KHÔNG được đọc")

student_interests = Table(
    "student_interests", metadata,
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id"), primary_key=True, index=True),
    Column("weight", Numeric(4, 2), nullable=False, server_default="1", comment="1 = sở thích chính, 0,5 = phụ"),
    created_at(),
    CheckConstraint("weight > 0 AND weight <= 1", name="weight"),
    comment="Chủ đề sinh viên tự khai là thích – tín hiệu PHỤ; tín hiệu chính là kết quả học tập")

course_results = Table(
    "course_results", metadata, pk(),
    fk("student_id", "students.id", ondelete="CASCADE"),
    fk("course_id", "courses.id"),
    fk("term_id", "terms.id"),
    Column("attempt_no", Integer, nullable=False, server_default="1"),
    Column("score", Numeric(4, 2), comment="Điểm thang của CTĐT; NULL khi miễn"),
    Column("letter_grade", String(3)),
    Column("grade_point", Numeric(3, 2)),
    Column("status", String(20), nullable=False),
    created_at(),
    UniqueConstraint("student_id", "course_id", "term_id"),
    CheckConstraint("status IN ('passed', 'failed', 'exempted', 'withdrawn', 'in_progress')", name="status"),
    CheckConstraint("status IN ('exempted', 'withdrawn', 'in_progress') OR score IS NOT NULL", name="score_required"),
    CheckConstraint("score IS NULL OR score >= 0", name="score_non_negative"),
    comment="Kết quả học tập: mỗi dòng là một lần học một học phần")

course_registrations = Table(
    "course_registrations", metadata, pk(),
    fk("student_id", "students.id", ondelete="CASCADE"),
    fk("course_id", "courses.id"),
    fk("term_id", "terms.id"),
    Column("status", String(20), nullable=False),
    Column("source", String(20), nullable=False),
    created_at(),
    UniqueConstraint("student_id", "course_id", "term_id"),
    CheckConstraint("status IN ('planned', 'registered', 'dropped')", name="status"),
    CheckConstraint("source IN ('student', 'simulated', 'imported')", name="source"),
    comment="Đăng ký học phần (với dữ liệu tự tạo: đáp án để đo độ chính xác gợi ý)")

# ======================= Kết quả gợi ý (ghi log cho production) =======================
recommendation_runs = Table(
    "recommendation_runs", metadata, pk(),
    fk("student_id", "students.id", ondelete="CASCADE"),
    fk("student_program_id", "student_programs.id"),
    fk("term_id", "terms.id"),
    Column("algorithm", String(50), nullable=False),
    Column("algorithm_version", String(20), nullable=False),
    Column("parameters", JSONB, comment="Trọng số, bộ lọc… của lần chạy"),
    created_at())

recommendation_items = Table(
    "recommendation_items", metadata, pk(),
    fk("run_id", "recommendation_runs.id", ondelete="CASCADE"),
    fk("course_id", "courses.id"),
    Column("rank", Integer, nullable=False),
    Column("score", Numeric(8, 4), nullable=False),
    Column("explanation", JSONB, comment="Đóng góp từng tiêu chí, lý do"),
    UniqueConstraint("run_id", "rank"))

recommendation_feedback = Table(
    "recommendation_feedback", metadata, pk(),
    fk("item_id", "recommendation_items.id", ondelete="CASCADE"),
    Column("action", String(20), nullable=False),
    created_at(),
    CheckConstraint("action IN ('viewed', 'accepted', 'rejected', 'registered')", name="action"))

Index("ix_course_results_student_course", course_results.c.student_id, course_results.c.course_id)
# Mỗi sinh viên tối đa MỘT chương trình chính (song ngành thì chương trình thứ hai có is_primary = false)
Index("uq_student_programs_one_primary", student_programs.c.student_id, unique=True,
      postgresql_where=student_programs.c.is_primary)
# Mỗi học phần đúng một chủ đề chính
Index("uq_course_topics_one_primary", course_topics.c.course_id, unique=True,
      postgresql_where=course_topics.c.is_primary)
