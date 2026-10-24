"""Schema Pydantic cho hồ sơ sinh viên và trạng thái học phần theo hợp đồng mục 6.4 và 6.5."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CourseStatusCode = Literal["passed", "block_complete", "missing_prerequisite", "retake", "eligible"]


class StudentProfileBlockOut(BaseModel):
    """Tiến độ của một khối kiến thức trong hồ sơ sinh viên (mục 6.4)."""
    block_code: str
    required_credits: int
    earned_credits: int
    counts_toward_total: bool


class StudentProfileOut(BaseModel):
    """Hồ sơ tiến độ học tập của sinh viên (mục 6.4)."""
    university_code: str
    student_code: str
    full_name: str
    curriculum_code: str
    major_code: str
    major_name: str
    cohort_year: int
    year_of_study: int
    term: str
    target_semester: int
    credits_earned: int
    credits_outstanding: int
    total_credits: int
    gpa: float | None = None
    max_credits_per_term: int
    interests: list[str] = Field(default_factory=list)
    outstanding_courses: list[str] = Field(default_factory=list)
    blocks: list[StudentProfileBlockOut] = Field(default_factory=list)


class LastAttemptOut(BaseModel):
    """Thông tin lần học gần nhất (mục 6.5)."""
    term_code: str
    attempt_no: int
    score: float | None = None
    letter_grade: str | None = None


class StatusBlockDetailOut(BaseModel):
    """Thông tin khối tự chọn đã hoàn thành (mục 6.5)."""
    block_code: str
    block_name: str
    required_credits: int
    earned_credits: int


class CourseStatusItemOut(BaseModel):
    """Trạng thái một học phần đối với một sinh viên (mục 6.5)."""
    course_code: str
    course_name: str
    credits: int
    block_code: str
    status: CourseStatusCode
    missing_prerequisites: list[list[str]] | None = None
    block: StatusBlockDetailOut | None = None
    last_attempt: LastAttemptOut | None = None
    text: str | None = None


class CourseStatusSummaryOut(BaseModel):
    """Tổng hợp số lượng học phần theo từng trạng thái (mục 6.5)."""
    passed: int = 0
    retake: int = 0
    eligible: int = 0
    missing_prerequisite: int = 0
    block_complete: int = 0


class CourseStatusOut(BaseModel):
    """Phản hồi trạng thái toàn bộ học phần của khung (mục 6.5)."""
    university_code: str
    student_code: str
    curriculum_code: str
    term: str
    summary: CourseStatusSummaryOut
    courses: list[CourseStatusItemOut]
