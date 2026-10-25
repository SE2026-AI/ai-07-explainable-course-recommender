"""Schema Pydantic cho gợi ý học phần và kiểm tra kế hoạch học kỳ (mục 6.6 và 6.7)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas.students import CourseStatusItemOut


class AssumptionIn(BaseModel):
    """Giả định kết quả học tập cho kịch bản what-if (mục 6.6)."""
    model_config = ConfigDict(extra="forbid")

    course_code: str
    status: Literal["passed", "failed"]
    score: float | None = None


class SwapIn(BaseModel):
    """Một cặp đổi môn: bỏ `course_code`, đưa `replacement` vào `items` (mục 6.6)."""
    model_config = ConfigDict(extra="forbid")

    course_code: str
    replacement: str


class RecommendationBodyIn(BaseModel):
    """Body gửi lên cho POST /v1/.../recommendations (mục 6.6).

    Hình dạng body do schema kiểm; nội dung (mã thuộc khung, đúng trạng thái, không lặp) do tầng xếp hạng kiểm.
    """
    model_config = ConfigDict(extra="forbid")

    term: str | None = None
    limit: int = Field(default=5, ge=1, le=20)
    weights: dict[str, float] | None = None
    assumptions: list[AssumptionIn] = Field(default_factory=list)
    skip: list[str] = Field(default_factory=list)
    swap: list[SwapIn] = Field(default_factory=list)


class RecommendationReasonOut(BaseModel):
    """Lý do và điểm đóng góp cho một học phần được gợi ý (mục 4.4 và 6.6)."""
    code: str
    contribution: float
    text: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class RecommendationItemOut(BaseModel):
    """Một học phần được gợi ý trong items (mục 6.6)."""
    rank: int
    course_code: str
    course_name: str
    credits: int
    block_code: str
    status: Literal["retake", "eligible"]
    score: float
    reasons: list[RecommendationReasonOut] = Field(default_factory=list)


class RecommendationsOut(BaseModel):
    """Phản hồi đầy đủ của endpoint gợi ý học phần (mục 6.6)."""
    university_code: str
    student_code: str
    curriculum_code: str
    term: str
    algorithm_version: str
    what_if: bool
    weights: dict[str, float]
    candidate_count: int
    items: list[RecommendationItemOut] = Field(default_factory=list)
    not_eligible: list[CourseStatusItemOut] = Field(default_factory=list)


class PlanCheckBodyIn(BaseModel):
    """Body gửi lên cho POST /v1/.../plan-check (mục 6.7)."""
    model_config = ConfigDict(extra="forbid")

    term: str | None = None
    course_codes: list[str] = Field(default_factory=list)


class PlanViolationOut(BaseModel):
    """Một vi phạm trong kế hoạch học kỳ (mục 4.5 và 6.7)."""
    code: str
    course_code: str | None = None
    text: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class PlanCheckOut(BaseModel):
    """Kết quả kiểm tra kế hoạch học kỳ (mục 6.7)."""
    university_code: str
    student_code: str
    term: str
    total_credits: int
    max_credits_per_term: int
    valid: bool
    violations: list[PlanViolationOut] = Field(default_factory=list)

