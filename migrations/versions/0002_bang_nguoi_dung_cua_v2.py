"""Lược đồ 4.0.0 của v2: tài khoản và dữ liệu người dùng.

Tám bảng của hợp đồng v2 mục 8: users, sessions, login_attempts, student_profiles, transcript_results, study_plans,
study_plan_versions, plan_undo_snapshots. Chỉ có khóa ngoại giữa chúng với nhau, không tới bảng tham chiếu, nên
nạp lại dữ liệu tham chiếu không đụng tới chúng. Không đổi bảng nào của 0001.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True, comment="SHA-256 của địa chỉ IP, không lưu IP gốc"),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_attempts")),
        comment="Lần đăng nhập, để giới hạn số lần sai (hợp đồng v2 mục 2.3); dòng cũ hơn một ngày được xóa",
    )
    op.create_index("ix_login_attempts_email_created_at", "login_attempts", ["email", "created_at"], unique=False)
    op.create_index("ix_login_attempts_ip_hash_created_at", "login_attempts", ["ip_hash", "created_at"], unique=False)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "public_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="`user_id` trong API; `id` không bao giờ ra ngoài",
        ),
        sa.Column("email", sa.String(length=254), nullable=False, comment="Đã chuẩn hóa: bỏ khoảng trắng, chữ thường"),
        sa.Column("password_hash", sa.Text(), nullable=False, comment="argon2id; không bao giờ trả về hay ghi log"),
        sa.Column("role", sa.String(length=20), server_default="student", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("role IN ('student', 'admin')", name=op.f("ck_users_role")),
        sa.CheckConstraint("email = lower(btrim(email))", name=op.f("ck_users_email_normalized")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("public_id", name=op.f("uq_users_public_id")),
        comment="Tài khoản: sinh viên tự đăng ký bằng email và mật khẩu; admin tạo bằng tools.create_admin",
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, comment="SHA-256 (hex) của giá trị cookie"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_sessions_expiry")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
        comment="Phiên đăng nhập; database chỉ giữ SHA-256 của token nên lộ database không lộ phiên",
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)
    op.create_table(
        "student_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("university_code", sa.String(length=20), nullable=False),
        sa.Column("curriculum_code", sa.String(length=50), nullable=False),
        sa.Column("cohort_year", sa.Integer(), nullable=True),
        sa.Column("semesters_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "transcript_updated_at", sa.DateTime(timezone=True), nullable=True, comment="NULL = chưa lưu bảng điểm lần nào"
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "cohort_year IS NULL OR cohort_year BETWEEN 2000 AND 2100", name=op.f("ck_student_profiles_cohort_year")
        ),
        sa.CheckConstraint("semesters_completed BETWEEN 0 AND 12", name=op.f("ck_student_profiles_semesters_completed")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_student_profiles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_student_profiles")),
        comment="Khung sinh viên chọn và số kỳ đã học; ghi khung bằng mã, không bằng khóa ngoại",
    )
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False, comment="Kỳ thứ mấy của sinh viên, không phải mã học kỳ"),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "course_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Mảng mã học phần theo thứ tự sinh viên xếp",
        ),
        sa.Column("min_credits", sa.Integer(), nullable=True),
        sa.Column("max_credits", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("jsonb_typeof(course_codes) = 'array'", name=op.f("ck_study_plans_course_codes_array")),
        sa.CheckConstraint("semester BETWEEN 1 AND 12", name=op.f("ck_study_plans_semester")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_study_plans_version")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_study_plans_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plans")),
        sa.UniqueConstraint("user_id", "semester", name=op.f("uq_study_plans_user_id_semester")),
        comment="Kế hoạch học kỳ hiện tại: mỗi sinh viên một kế hoạch cho mỗi kỳ",
    )
    op.create_index(op.f("ix_study_plans_user_id"), "study_plans", ["user_id"], unique=False)
    op.create_table(
        "transcript_results",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_code", sa.String(length=20), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(precision=4, scale=2), nullable=True, comment="NULL khi miễn"),
        sa.Column("exempted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "(exempted AND score IS NULL) OR (NOT exempted AND score IS NOT NULL AND score >= 0)",
            name=op.f("ck_transcript_results_score_or_exempted"),
        ),
        sa.CheckConstraint("semester BETWEEN 1 AND 12", name=op.f("ck_transcript_results_semester")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_transcript_results_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transcript_results")),
        sa.UniqueConstraint("user_id", "course_code", name=op.f("uq_transcript_results_user_id_course_code")),
        comment="Bảng điểm đã lưu: mỗi môn một dòng = lần học gần nhất, đúng một dòng results[] của §6.10 v1",
    )
    op.create_index(op.f("ix_transcript_results_user_id"), "transcript_results", ["user_id"], unique=False)
    op.create_table(
        "plan_undo_snapshots",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, comment="SHA-256 (hex) của undo_token"),
        sa.Column("version_before", sa.Integer(), nullable=False, comment="Phiên bản ngay trước lần bỏ môn; undo khôi phục nó"),
        sa.Column("version_after", sa.Integer(), nullable=False, comment="Phiên bản do lần bỏ môn tạo ra"),
        sa.Column("removed_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "consumed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="NULL = chưa hoàn tác; mỗi lần bỏ chỉ hoàn tác một lần",
        ),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_plan_undo_snapshots_expiry")),
        sa.CheckConstraint("version_after > version_before", name=op.f("ck_plan_undo_snapshots_versions")),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["study_plans.id"], name=op.f("fk_plan_undo_snapshots_plan_id_study_plans"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_undo_snapshots")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_plan_undo_snapshots_token_hash")),
        comment="Một lần bỏ môn khỏi kế hoạch, để hoàn tác (VT-097 chuyển sang v2, hợp đồng v2 mục 6.12)",
    )
    op.create_index(op.f("ix_plan_undo_snapshots_plan_id"), "plan_undo_snapshots", ["plan_id"], unique=False)
    op.create_table(
        "study_plan_versions",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("course_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("min_credits", sa.Integer(), nullable=True),
        sa.Column("max_credits", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("jsonb_typeof(course_codes) = 'array'", name=op.f("ck_study_plan_versions_course_codes_array")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_study_plan_versions_version")),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["study_plans.id"], name=op.f("fk_study_plan_versions_plan_id_study_plans"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plan_versions")),
        sa.UniqueConstraint("plan_id", "version", name=op.f("uq_study_plan_versions_plan_id_version")),
        comment="Mọi phiên bản đã lưu của một kế hoạch, kể cả phiên bản hiện tại; để hoàn tác",
    )
    op.create_index(op.f("ix_study_plan_versions_plan_id"), "study_plan_versions", ["plan_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_study_plan_versions_plan_id"), table_name="study_plan_versions")
    op.drop_table("study_plan_versions")
    op.drop_index(op.f("ix_plan_undo_snapshots_plan_id"), table_name="plan_undo_snapshots")
    op.drop_table("plan_undo_snapshots")
    op.drop_index(op.f("ix_transcript_results_user_id"), table_name="transcript_results")
    op.drop_table("transcript_results")
    op.drop_index(op.f("ix_study_plans_user_id"), table_name="study_plans")
    op.drop_table("study_plans")
    op.drop_table("student_profiles")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_index("ix_login_attempts_ip_hash_created_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_email_created_at", table_name="login_attempts")
    op.drop_table("login_attempts")
