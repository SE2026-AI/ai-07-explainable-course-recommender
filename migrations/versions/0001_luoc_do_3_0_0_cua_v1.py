"""Lược đồ 3.0.0 của v1: mọi bảng tham chiếu, bảng sinh viên giả lập và các view.

Sinh bằng autogenerate từ `src/data/db/schema.py` ở commit b2dea13 (main trước v2). SQL của view được chép cố định
vào đây thay vì import từ `src/data/db/views.py`, để sửa view về sau không làm đổi một migration đã chạy.

Database dựng bằng `build()` của v1 đã có sẵn mọi thứ ở đây: `src/data/db/migrate.py` đánh dấu nó ở `0001` thay
vì chạy lại.

Revision ID: 0001
Revises:
Create Date: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# View của lược đồ 3.0.0, chép nguyên văn từ src/data/db/views.py tại b2dea13.
VIEWS = {
    "v_curriculum_courses": """
        SELECT cu.id AS curriculum_id, cu.code AS curriculum_code, u.code AS university_code,
               c.id AS course_id, c.code AS course_code, c.name AS course_name, c.name_en AS course_name_en,
               c.credits, c.teaching_language,
               b.id AS block_id, b.code AS block_code, b.name AS block_name, b.selection_rule,
               CASE WHEN b.selection_rule = 'all' THEN 1 ELSE 0 END AS is_required,
               b.required_credits AS block_required_credits,
               CASE WHEN b.counts_toward_total THEN 1 ELSE 0 END AS counts_toward_total,
               cc.recommended_semester, (cc.recommended_semester + 1) / 2 AS recommended_year, cc.sort_no
        FROM curriculum_courses cc
        JOIN curricula cu ON cu.id = cc.curriculum_id
        JOIN majors m ON m.id = cu.major_id
        JOIN universities u ON u.id = m.university_id
        JOIN courses c ON c.id = cc.course_id
        JOIN curriculum_blocks b ON b.id = cc.block_id
    """,
    "v_prerequisites": """
        SELECT cc.curriculum_id, c.code AS course_code, p.group_no, p.required_course_code, p.requirement_type,
               p.min_score,
               CASE WHEN EXISTS (SELECT 1 FROM curriculum_courses x
                                 WHERE x.curriculum_id = cc.curriculum_id AND x.course_id = p.required_course_id)
                    THEN 1 ELSE 0 END AS in_curriculum
        FROM prerequisites p
        JOIN curriculum_courses cc ON cc.id = p.curriculum_course_id
        JOIN courses c ON c.id = cc.course_id
    """,
    "v_student_programs": """
        SELECT s.id AS student_id, u.code AS university_code, s.student_code, s.full_name, s.is_synthetic,
               sp.id AS student_program_id, cu.id AS curriculum_id, cu.code AS curriculum_code,
               m.code AS major_code, m.name AS major_name, sp.cohort_year, sp.status, sp.is_primary
        FROM students s
        JOIN universities u ON u.id = s.university_id
        JOIN student_programs sp ON sp.student_id = s.id
        JOIN curricula cu ON cu.id = sp.curriculum_id
        JOIN majors m ON m.id = cu.major_id
    """,
    "v_course_results": """
        SELECT r.id AS result_id, r.student_id, c.code AS course_code, r.course_id, t.code AS term_code,
               r.attempt_no, r.score, r.letter_grade, r.grade_point, r.status,
               ROW_NUMBER() OVER (PARTITION BY r.student_id, r.course_id
                                  ORDER BY t.code DESC, r.attempt_no DESC) AS recency
        FROM course_results r
        JOIN courses c ON c.id = r.course_id
        JOIN terms t ON t.id = r.term_id
    """,
    "v_student_progress": """
        SELECT sp.student_id, sp.id AS student_program_id,
               COALESCE(SUM(c.credits) FILTER (WHERE r.status IN ('passed', 'exempted') AND b.counts_toward_total), 0)
                   AS credits_earned,
               COALESCE(SUM(c.credits) FILTER (WHERE r.status = 'failed' AND b.counts_toward_total), 0)
                   AS credits_outstanding,
               ROUND(SUM(r.grade_point * c.credits) FILTER (WHERE r.status IN ('passed', 'failed') AND b.counts_toward_total)
                     / NULLIF(SUM(c.credits) FILTER (WHERE r.status IN ('passed', 'failed') AND b.counts_toward_total), 0), 2)
                   AS gpa,
               COUNT(DISTINCT r.term_code) AS terms_studied
        FROM student_programs sp
        LEFT JOIN v_course_results r ON r.student_id = sp.student_id AND r.recency = 1
        LEFT JOIN courses c ON c.id = r.course_id
        LEFT JOIN curriculum_courses cc ON cc.curriculum_id = sp.curriculum_id AND cc.course_id = r.course_id
        LEFT JOIN curriculum_blocks b ON b.id = cc.block_id
        WHERE sp.is_primary
        GROUP BY sp.student_id, sp.id
    """,
}


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_app_settings")),
    )
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("document_number", sa.String(length=50), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("issuer", sa.Text(), nullable=True),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_sources")),
        sa.UniqueConstraint("code", name=op.f("uq_data_sources_code")),
        comment="Văn bản/nguồn mà dữ liệu được lấy ra; mọi dữ liệu tham chiếu đều truy được về đây",
    )
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint("code", name=op.f("uq_skills_code")),
        comment="Kỹ năng mà học phần rèn luyện (danh mục do nhóm tự gán)",
    )
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
        sa.UniqueConstraint("code", name=op.f("uq_topics_code")),
        comment="Chủ đề học phần; dùng để nhóm các môn liên quan và cho sinh viên khai sở thích",
    )
    op.create_table(
        "universities",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=True),
        sa.Column("short_name", sa.String(length=50), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_universities")),
        sa.UniqueConstraint("code", name=op.f("uq_universities_code")),
        comment="Trường đại học. Mỗi trường độc lập: có ngành, học phần, thang điểm, lịch học kỳ riêng",
    )
    op.create_table(
        "academic_years",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("university_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["university_id"], ["universities.id"], name=op.f("fk_academic_years_university_id_universities"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_academic_years")),
        sa.UniqueConstraint("university_id", "code", name=op.f("uq_academic_years_university_id_code")),
    )
    op.create_index(op.f("ix_academic_years_university_id"), "academic_years", ["university_id"], unique=False)
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("university_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=True),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("lecture_hours", sa.Integer(), nullable=True),
        sa.Column("practice_hours", sa.Integer(), nullable=True),
        sa.Column("self_study_hours", sa.Integer(), nullable=True),
        sa.Column("teaching_language", sa.String(length=5), server_default="vi", nullable=False),
        sa.CheckConstraint("credits > 0", name=op.f("ck_courses_credits")),
        sa.ForeignKeyConstraint(
            ["university_id"], ["universities.id"], name=op.f("fk_courses_university_id_universities"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("university_id", "code", name=op.f("uq_courses_university_id_code")),
        comment="Học phần của một trường, dùng chung cho mọi CTĐT của trường đó",
    )
    op.create_index(op.f("ix_courses_university_id"), "courses", ["university_id"], unique=False)
    op.create_table(
        "data_issues",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_key", sa.String(length=100), nullable=False),
        sa.Column("issue_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.CheckConstraint("status IN ('open', 'resolved_in_data', 'closed')", name=op.f("ck_data_issues_status")),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], name=op.f("fk_data_issues_source_id_data_sources"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_issues")),
        comment="Chỗ văn bản gốc mâu thuẫn hoặc thiếu; ghi lại thay vì âm thầm sửa",
    )
    op.create_index(op.f("ix_data_issues_source_id"), "data_issues", ["source_id"], unique=False)
    op.create_table(
        "faculties",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("university_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["university_id"], ["universities.id"], name=op.f("fk_faculties_university_id_universities"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_faculties")),
        sa.UniqueConstraint("university_id", "code", name=op.f("uq_faculties_university_id_code")),
    )
    op.create_index(op.f("ix_faculties_university_id"), "faculties", ["university_id"], unique=False)
    op.create_table(
        "grading_schemes",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("university_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("max_score", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("pass_score", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("pass_score > 0 AND pass_score <= max_score", name=op.f("ck_grading_schemes_pass_score")),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], name=op.f("fk_grading_schemes_source_id_data_sources"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name=op.f("fk_grading_schemes_university_id_universities"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grading_schemes")),
        sa.UniqueConstraint("code", name=op.f("uq_grading_schemes_code")),
    )
    op.create_index(op.f("ix_grading_schemes_source_id"), "grading_schemes", ["source_id"], unique=False)
    op.create_index(op.f("ix_grading_schemes_university_id"), "grading_schemes", ["university_id"], unique=False)
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("university_id", sa.Integer(), nullable=False),
        sa.Column(
            "student_code", sa.String(length=30), nullable=False, comment="Mã sinh viên do trường cấp; chỉ duy nhất trong trường"
        ),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(
            ["university_id"], ["universities.id"], name=op.f("fk_students_university_id_universities"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint("university_id", "student_code", name=op.f("uq_students_university_id_student_code")),
        comment="Sinh viên. Khóa là id; (university_id, student_code) là khóa nghiệp vụ",
    )
    op.create_index(op.f("ix_students_university_id"), "students", ["university_id"], unique=False)
    op.create_table(
        "course_equivalences",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("equivalent_course_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint("course_id <> equivalent_course_id", name=op.f("ck_course_equivalences_not_self")),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_course_equivalences_course_id_courses"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["equivalent_course_id"],
            ["courses.id"],
            name=op.f("fk_course_equivalences_equivalent_course_id_courses"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], name=op.f("fk_course_equivalences_source_id_data_sources"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_equivalences")),
        sa.UniqueConstraint(
            "course_id", "equivalent_course_id", name=op.f("uq_course_equivalences_course_id_equivalent_course_id")
        ),
        comment="Học phần tương đương/thay thế",
    )
    op.create_index(op.f("ix_course_equivalences_course_id"), "course_equivalences", ["course_id"], unique=False)
    op.create_index(
        op.f("ix_course_equivalences_equivalent_course_id"), "course_equivalences", ["equivalent_course_id"], unique=False
    )
    op.create_index(op.f("ix_course_equivalences_source_id"), "course_equivalences", ["source_id"], unique=False)
    op.create_table(
        "course_skills",
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Numeric(precision=4, scale=2), server_default="1", nullable=False),
        sa.CheckConstraint("weight > 0", name=op.f("ck_course_skills_weight")),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_course_skills_course_id_courses"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_course_skills_skill_id_skills")),
        sa.PrimaryKeyConstraint("course_id", "skill_id", name=op.f("pk_course_skills")),
        comment="Học phần rèn kỹ năng nào, mức độ (weight)",
    )
    op.create_index(op.f("ix_course_skills_skill_id"), "course_skills", ["skill_id"], unique=False)
    op.create_table(
        "course_topics",
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_course_topics_course_id_courses"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name=op.f("fk_course_topics_topic_id_topics")),
        sa.PrimaryKeyConstraint("course_id", "topic_id", name=op.f("pk_course_topics")),
        comment="Học phần thuộc chủ đề nào; mỗi học phần có đúng một chủ đề chính",
    )
    op.create_index(op.f("ix_course_topics_topic_id"), "course_topics", ["topic_id"], unique=False)
    op.create_index("uq_course_topics_one_primary", "course_topics", ["course_id"], unique=True, postgresql_where="is_primary")
    op.create_table(
        "grade_conversions",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("grading_scheme_id", sa.Integer(), nullable=False),
        sa.Column("letter", sa.String(length=3), nullable=False),
        sa.Column("min_score", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("max_score", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("grade_point", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("is_pass", sa.Boolean(), nullable=False),
        sa.CheckConstraint("min_score <= max_score", name=op.f("ck_grade_conversions_range")),
        sa.ForeignKeyConstraint(
            ["grading_scheme_id"],
            ["grading_schemes.id"],
            name=op.f("fk_grade_conversions_grading_scheme_id_grading_schemes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grade_conversions")),
        sa.UniqueConstraint("grading_scheme_id", "letter", name=op.f("uq_grade_conversions_grading_scheme_id_letter")),
    )
    op.create_index(op.f("ix_grade_conversions_grading_scheme_id"), "grade_conversions", ["grading_scheme_id"], unique=False)
    op.create_table(
        "majors",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("university_id", sa.Integer(), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=20), nullable=False, comment="Mã ngành theo Bộ GD&ĐT, ví dụ 7460108"),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=True),
        sa.Column("degree_level", sa.String(length=20), nullable=False),
        sa.Column("is_pilot", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="Ngành đào tạo thí điểm"),
        sa.CheckConstraint("degree_level IN ('bachelor', 'engineer', 'master', 'doctor')", name=op.f("ck_majors_degree_level")),
        sa.ForeignKeyConstraint(
            ["faculty_id"], ["faculties.id"], name=op.f("fk_majors_faculty_id_faculties"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["university_id"], ["universities.id"], name=op.f("fk_majors_university_id_universities"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_majors")),
        sa.UniqueConstraint("university_id", "code", name=op.f("uq_majors_university_id_code")),
        comment="Ngành đào tạo của một trường",
    )
    op.create_index(op.f("ix_majors_faculty_id"), "majors", ["faculty_id"], unique=False)
    op.create_index(op.f("ix_majors_university_id"), "majors", ["university_id"], unique=False)
    op.create_table(
        "student_attributes",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("attribute_code", sa.String(length=30), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_student_attributes_student_id_students"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("student_id", "attribute_code", name=op.f("pk_student_attributes")),
        comment="DỮ LIỆU NHẠY CẢM, chỉ dùng để đánh giá công bằng; thuật toán gợi ý KHÔNG được đọc",
    )
    op.create_table(
        "student_interests",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column(
            "weight",
            sa.Numeric(precision=4, scale=2),
            server_default="1",
            nullable=False,
            comment="1 = sở thích chính, 0,5 = phụ",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("weight > 0 AND weight <= 1", name=op.f("ck_student_interests_weight")),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_student_interests_student_id_students"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name=op.f("fk_student_interests_topic_id_topics")),
        sa.PrimaryKeyConstraint("student_id", "topic_id", name=op.f("pk_student_interests")),
        comment="Chủ đề sinh viên tự khai là thích – tín hiệu PHỤ; tín hiệu chính là kết quả học tập",
    )
    op.create_index(op.f("ix_student_interests_topic_id"), "student_interests", ["topic_id"], unique=False)
    op.create_table(
        "terms",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("university_id", sa.Integer(), nullable=False, comment="Trường sở hữu lịch học kỳ"),
        sa.Column("academic_year_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False, comment="NNNNK: năm bắt đầu + kỳ (3 = hè)"),
        sa.Column("term_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.CheckConstraint("term_no IN (1, 2, 3)", name=op.f("ck_terms_term_no")),
        sa.ForeignKeyConstraint(
            ["academic_year_id"],
            ["academic_years.id"],
            name=op.f("fk_terms_academic_year_id_academic_years"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["university_id"], ["universities.id"], name=op.f("fk_terms_university_id_universities"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_terms")),
        sa.UniqueConstraint("university_id", "code", name=op.f("uq_terms_university_id_code")),
    )
    op.create_index(op.f("ix_terms_academic_year_id"), "terms", ["academic_year_id"], unique=False)
    op.create_index(op.f("ix_terms_university_id"), "terms", ["university_id"], unique=False)
    op.create_table(
        "course_registrations",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("source IN ('student', 'simulated', 'imported')", name=op.f("ck_course_registrations_source")),
        sa.CheckConstraint("status IN ('planned', 'registered', 'dropped')", name=op.f("ck_course_registrations_status")),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_course_registrations_course_id_courses"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_course_registrations_student_id_students"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["term_id"], ["terms.id"], name=op.f("fk_course_registrations_term_id_terms"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_registrations")),
        sa.UniqueConstraint(
            "student_id", "course_id", "term_id", name=op.f("uq_course_registrations_student_id_course_id_term_id")
        ),
        comment="Đăng ký học phần (với dữ liệu tự tạo: đáp án để đo độ chính xác gợi ý)",
    )
    op.create_index(op.f("ix_course_registrations_course_id"), "course_registrations", ["course_id"], unique=False)
    op.create_index(op.f("ix_course_registrations_student_id"), "course_registrations", ["student_id"], unique=False)
    op.create_index(op.f("ix_course_registrations_term_id"), "course_registrations", ["term_id"], unique=False)
    op.create_table(
        "course_results",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), server_default="1", nullable=False),
        sa.Column("score", sa.Numeric(precision=4, scale=2), nullable=True, comment="Điểm thang của CTĐT; NULL khi miễn"),
        sa.Column("letter_grade", sa.String(length=3), nullable=True),
        sa.Column("grade_point", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "status IN ('exempted', 'withdrawn', 'in_progress') OR score IS NOT NULL",
            name=op.f("ck_course_results_score_required"),
        ),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'exempted', 'withdrawn', 'in_progress')", name=op.f("ck_course_results_status")
        ),
        sa.CheckConstraint("score IS NULL OR score >= 0", name=op.f("ck_course_results_score_non_negative")),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_course_results_course_id_courses"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_course_results_student_id_students"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"], name=op.f("fk_course_results_term_id_terms"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_results")),
        sa.UniqueConstraint("student_id", "course_id", "term_id", name=op.f("uq_course_results_student_id_course_id_term_id")),
        comment="Kết quả học tập: mỗi dòng là một lần học một học phần",
    )
    op.create_index(op.f("ix_course_results_course_id"), "course_results", ["course_id"], unique=False)
    op.create_index("ix_course_results_student_course", "course_results", ["student_id", "course_id"], unique=False)
    op.create_index(op.f("ix_course_results_student_id"), "course_results", ["student_id"], unique=False)
    op.create_index(op.f("ix_course_results_term_id"), "course_results", ["term_id"], unique=False)
    op.create_table(
        "curricula",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False, comment="TRƯỜNG-MÃNGÀNH-KHÓA, ví dụ HUS-7460108-2022"),
        sa.Column("major_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=True),
        sa.Column("program_type", sa.String(length=30), nullable=False),
        sa.Column("effective_from_cohort", sa.Integer(), nullable=False),
        sa.Column("effective_to_cohort", sa.Integer(), nullable=True, comment="NULL = còn áp dụng"),
        sa.Column("total_credits", sa.Integer(), nullable=False),
        sa.Column("standard_semesters", sa.Integer(), nullable=False),
        sa.Column("max_credits_per_term", sa.Integer(), nullable=False),
        sa.Column("grading_scheme_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'active', 'retired')", name=op.f("ck_curricula_status")),
        sa.CheckConstraint(
            "effective_to_cohort IS NULL OR effective_to_cohort >= effective_from_cohort", name=op.f("ck_curricula_cohort_range")
        ),
        sa.CheckConstraint("total_credits > 0 AND standard_semesters > 0", name=op.f("ck_curricula_positive")),
        sa.ForeignKeyConstraint(
            ["grading_scheme_id"],
            ["grading_schemes.id"],
            name=op.f("fk_curricula_grading_scheme_id_grading_schemes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["major_id"], ["majors.id"], name=op.f("fk_curricula_major_id_majors"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], name=op.f("fk_curricula_source_id_data_sources"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curricula")),
        sa.UniqueConstraint("code", name=op.f("uq_curricula_code")),
        comment="Khung chương trình đào tạo: một phiên bản của một ngành, áp dụng cho một dải khóa",
    )
    op.create_index(op.f("ix_curricula_grading_scheme_id"), "curricula", ["grading_scheme_id"], unique=False)
    op.create_index(op.f("ix_curricula_major_id"), "curricula", ["major_id"], unique=False)
    op.create_index(op.f("ix_curricula_source_id"), "curricula", ["source_id"], unique=False)
    op.create_table(
        "curriculum_blocks",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("curriculum_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False, comment="Số mục trong văn bản: I, II, V.2.1…"),
        sa.Column("parent_block_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "selection_rule",
            sa.String(length=20),
            nullable=False,
            comment="all = học hết; choose_credits = chọn đủ required_credits; container = chỉ chứa khối con",
        ),
        sa.Column("required_credits", sa.Integer(), nullable=False),
        sa.Column("counts_toward_total", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "selection_rule IN ('all', 'choose_credits', 'container')", name=op.f("ck_curriculum_blocks_selection_rule")
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_id"], ["curricula.id"], name=op.f("fk_curriculum_blocks_curriculum_id_curricula"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parent_block_id"],
            ["curriculum_blocks.id"],
            name=op.f("fk_curriculum_blocks_parent_block_id_curriculum_blocks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_blocks")),
        sa.UniqueConstraint("curriculum_id", "code", name=op.f("uq_curriculum_blocks_curriculum_id_code")),
        comment="Khối kiến thức (cây). Nhóm tự chọn là khối có selection_rule = choose_credits",
    )
    op.create_index(op.f("ix_curriculum_blocks_curriculum_id"), "curriculum_blocks", ["curriculum_id"], unique=False)
    op.create_index(op.f("ix_curriculum_blocks_parent_block_id"), "curriculum_blocks", ["parent_block_id"], unique=False)
    op.create_table(
        "student_programs",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("curriculum_id", sa.Integer(), nullable=False),
        sa.Column("cohort_year", sa.Integer(), nullable=False, comment="Khóa tuyển sinh"),
        sa.Column("admission_term_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'graduated', 'suspended', 'withdrawn', 'transferred')", name=op.f("ck_student_programs_status")
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name=op.f("ck_student_programs_date_range")
        ),
        sa.ForeignKeyConstraint(
            ["admission_term_id"], ["terms.id"], name=op.f("fk_student_programs_admission_term_id_terms"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_id"], ["curricula.id"], name=op.f("fk_student_programs_curriculum_id_curricula"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_student_programs_student_id_students"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_programs")),
        sa.UniqueConstraint("student_id", "curriculum_id", name=op.f("uq_student_programs_student_id_curriculum_id")),
        comment="Sinh viên theo học CTĐT nào (cho phép chuyển ngành, học song ngành)",
    )
    op.create_index(op.f("ix_student_programs_admission_term_id"), "student_programs", ["admission_term_id"], unique=False)
    op.create_index(op.f("ix_student_programs_curriculum_id"), "student_programs", ["curriculum_id"], unique=False)
    op.create_index(op.f("ix_student_programs_student_id"), "student_programs", ["student_id"], unique=False)
    op.create_index(
        "uq_student_programs_one_primary", "student_programs", ["student_id"], unique=True, postgresql_where="is_primary"
    )
    op.create_table(
        "curriculum_courses",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("curriculum_id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("sort_no", sa.Integer(), nullable=True, comment="STT trong văn bản"),
        sa.Column("recommended_semester", sa.Integer(), nullable=True, comment="Kỳ thứ mấy của CTĐT nên học"),
        sa.Column("recommended_semester_source_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "recommended_semester IS NULL OR recommended_semester >= 1", name=op.f("ck_curriculum_courses_semester")
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["curriculum_blocks.id"],
            name=op.f("fk_curriculum_courses_block_id_curriculum_blocks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_curriculum_courses_course_id_courses"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_id"], ["curricula.id"], name=op.f("fk_curriculum_courses_curriculum_id_curricula"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["recommended_semester_source_id"],
            ["data_sources.id"],
            name=op.f("fk_curriculum_courses_recommended_semester_source_id_data_sources"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_courses")),
        sa.UniqueConstraint("curriculum_id", "course_id", name=op.f("uq_curriculum_courses_curriculum_id_course_id")),
        comment="Học phần thuộc khung nào, nằm trong khối nào",
    )
    op.create_index(op.f("ix_curriculum_courses_block_id"), "curriculum_courses", ["block_id"], unique=False)
    op.create_index(op.f("ix_curriculum_courses_course_id"), "curriculum_courses", ["course_id"], unique=False)
    op.create_index(op.f("ix_curriculum_courses_curriculum_id"), "curriculum_courses", ["curriculum_id"], unique=False)
    op.create_index(
        op.f("ix_curriculum_courses_recommended_semester_source_id"),
        "curriculum_courses",
        ["recommended_semester_source_id"],
        unique=False,
    )
    op.create_table(
        "recommendation_runs",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("student_program_id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("algorithm", sa.String(length=50), nullable=False),
        sa.Column("algorithm_version", sa.String(length=20), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Trọng số, bộ lọc… của lần chạy"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_recommendation_runs_student_id_students"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["student_program_id"],
            ["student_programs.id"],
            name=op.f("fk_recommendation_runs_student_program_id_student_programs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"], ["terms.id"], name=op.f("fk_recommendation_runs_term_id_terms"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_runs")),
    )
    op.create_index(op.f("ix_recommendation_runs_student_id"), "recommendation_runs", ["student_id"], unique=False)
    op.create_index(
        op.f("ix_recommendation_runs_student_program_id"), "recommendation_runs", ["student_program_id"], unique=False
    )
    op.create_index(op.f("ix_recommendation_runs_term_id"), "recommendation_runs", ["term_id"], unique=False)
    op.create_table(
        "prerequisites",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("curriculum_course_id", sa.Integer(), nullable=False),
        sa.Column("group_no", sa.Integer(), nullable=False, comment="Cùng group_no = HOẶC; khác group_no = VÀ"),
        sa.Column("required_course_code", sa.String(length=20), nullable=False, comment="Ghi nguyên văn từ văn bản"),
        sa.Column("required_course_id", sa.Integer(), nullable=True),
        sa.Column("requirement_type", sa.String(length=20), server_default="prerequisite", nullable=False),
        sa.Column("min_score", sa.Numeric(precision=4, scale=2), nullable=True, comment="NULL = chỉ cần đạt"),
        sa.CheckConstraint(
            "requirement_type IN ('prerequisite', 'prior', 'corequisite')", name=op.f("ck_prerequisites_requirement_type")
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_course_id"],
            ["curriculum_courses.id"],
            name=op.f("fk_prerequisites_curriculum_course_id_curriculum_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["required_course_id"], ["courses.id"], name=op.f("fk_prerequisites_required_course_id_courses"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prerequisites")),
        sa.UniqueConstraint(
            "curriculum_course_id",
            "group_no",
            "required_course_code",
            name=op.f("uq_prerequisites_curriculum_course_id_group_no_required_course_code"),
        ),
        comment="Điều kiện của học phần TRONG một CTĐT (mỗi văn bản tự quy định)",
    )
    op.create_index(op.f("ix_prerequisites_curriculum_course_id"), "prerequisites", ["curriculum_course_id"], unique=False)
    op.create_index(op.f("ix_prerequisites_required_course_id"), "prerequisites", ["required_course_id"], unique=False)
    op.create_table(
        "recommendation_items",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Đóng góp từng tiêu chí, lý do"),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_recommendation_items_course_id_courses"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["recommendation_runs.id"],
            name=op.f("fk_recommendation_items_run_id_recommendation_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_items")),
        sa.UniqueConstraint("run_id", "rank", name=op.f("uq_recommendation_items_run_id_rank")),
    )
    op.create_index(op.f("ix_recommendation_items_course_id"), "recommendation_items", ["course_id"], unique=False)
    op.create_index(op.f("ix_recommendation_items_run_id"), "recommendation_items", ["run_id"], unique=False)
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "action IN ('viewed', 'accepted', 'rejected', 'registered')", name=op.f("ck_recommendation_feedback_action")
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["recommendation_items.id"],
            name=op.f("fk_recommendation_feedback_item_id_recommendation_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_feedback")),
    )
    op.create_index(op.f("ix_recommendation_feedback_item_id"), "recommendation_feedback", ["item_id"], unique=False)

    for name, sql in VIEWS.items():
        op.execute(f"CREATE VIEW {name} AS {sql}")


def downgrade() -> None:
    for name in reversed(list(VIEWS)):
        op.execute(f"DROP VIEW IF EXISTS {name}")
    op.drop_index(op.f("ix_recommendation_feedback_item_id"), table_name="recommendation_feedback")
    op.drop_table("recommendation_feedback")
    op.drop_index(op.f("ix_recommendation_items_run_id"), table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_course_id"), table_name="recommendation_items")
    op.drop_table("recommendation_items")
    op.drop_index(op.f("ix_prerequisites_required_course_id"), table_name="prerequisites")
    op.drop_index(op.f("ix_prerequisites_curriculum_course_id"), table_name="prerequisites")
    op.drop_table("prerequisites")
    op.drop_index(op.f("ix_recommendation_runs_term_id"), table_name="recommendation_runs")
    op.drop_index(op.f("ix_recommendation_runs_student_program_id"), table_name="recommendation_runs")
    op.drop_index(op.f("ix_recommendation_runs_student_id"), table_name="recommendation_runs")
    op.drop_table("recommendation_runs")
    op.drop_index(op.f("ix_curriculum_courses_recommended_semester_source_id"), table_name="curriculum_courses")
    op.drop_index(op.f("ix_curriculum_courses_curriculum_id"), table_name="curriculum_courses")
    op.drop_index(op.f("ix_curriculum_courses_course_id"), table_name="curriculum_courses")
    op.drop_index(op.f("ix_curriculum_courses_block_id"), table_name="curriculum_courses")
    op.drop_table("curriculum_courses")
    op.drop_index("uq_student_programs_one_primary", table_name="student_programs", postgresql_where="is_primary")
    op.drop_index(op.f("ix_student_programs_student_id"), table_name="student_programs")
    op.drop_index(op.f("ix_student_programs_curriculum_id"), table_name="student_programs")
    op.drop_index(op.f("ix_student_programs_admission_term_id"), table_name="student_programs")
    op.drop_table("student_programs")
    op.drop_index(op.f("ix_curriculum_blocks_parent_block_id"), table_name="curriculum_blocks")
    op.drop_index(op.f("ix_curriculum_blocks_curriculum_id"), table_name="curriculum_blocks")
    op.drop_table("curriculum_blocks")
    op.drop_index(op.f("ix_curricula_source_id"), table_name="curricula")
    op.drop_index(op.f("ix_curricula_major_id"), table_name="curricula")
    op.drop_index(op.f("ix_curricula_grading_scheme_id"), table_name="curricula")
    op.drop_table("curricula")
    op.drop_index(op.f("ix_course_results_term_id"), table_name="course_results")
    op.drop_index(op.f("ix_course_results_student_id"), table_name="course_results")
    op.drop_index("ix_course_results_student_course", table_name="course_results")
    op.drop_index(op.f("ix_course_results_course_id"), table_name="course_results")
    op.drop_table("course_results")
    op.drop_index(op.f("ix_course_registrations_term_id"), table_name="course_registrations")
    op.drop_index(op.f("ix_course_registrations_student_id"), table_name="course_registrations")
    op.drop_index(op.f("ix_course_registrations_course_id"), table_name="course_registrations")
    op.drop_table("course_registrations")
    op.drop_index(op.f("ix_terms_university_id"), table_name="terms")
    op.drop_index(op.f("ix_terms_academic_year_id"), table_name="terms")
    op.drop_table("terms")
    op.drop_index(op.f("ix_student_interests_topic_id"), table_name="student_interests")
    op.drop_table("student_interests")
    op.drop_table("student_attributes")
    op.drop_index(op.f("ix_majors_university_id"), table_name="majors")
    op.drop_index(op.f("ix_majors_faculty_id"), table_name="majors")
    op.drop_table("majors")
    op.drop_index(op.f("ix_grade_conversions_grading_scheme_id"), table_name="grade_conversions")
    op.drop_table("grade_conversions")
    op.drop_index("uq_course_topics_one_primary", table_name="course_topics", postgresql_where="is_primary")
    op.drop_index(op.f("ix_course_topics_topic_id"), table_name="course_topics")
    op.drop_table("course_topics")
    op.drop_index(op.f("ix_course_skills_skill_id"), table_name="course_skills")
    op.drop_table("course_skills")
    op.drop_index(op.f("ix_course_equivalences_source_id"), table_name="course_equivalences")
    op.drop_index(op.f("ix_course_equivalences_equivalent_course_id"), table_name="course_equivalences")
    op.drop_index(op.f("ix_course_equivalences_course_id"), table_name="course_equivalences")
    op.drop_table("course_equivalences")
    op.drop_index(op.f("ix_students_university_id"), table_name="students")
    op.drop_table("students")
    op.drop_index(op.f("ix_grading_schemes_university_id"), table_name="grading_schemes")
    op.drop_index(op.f("ix_grading_schemes_source_id"), table_name="grading_schemes")
    op.drop_table("grading_schemes")
    op.drop_index(op.f("ix_faculties_university_id"), table_name="faculties")
    op.drop_table("faculties")
    op.drop_index(op.f("ix_data_issues_source_id"), table_name="data_issues")
    op.drop_table("data_issues")
    op.drop_index(op.f("ix_courses_university_id"), table_name="courses")
    op.drop_table("courses")
    op.drop_index(op.f("ix_academic_years_university_id"), table_name="academic_years")
    op.drop_table("academic_years")
    op.drop_table("universities")
    op.drop_table("topics")
    op.drop_table("skills")
    op.drop_table("data_sources")
    op.drop_table("app_settings")
