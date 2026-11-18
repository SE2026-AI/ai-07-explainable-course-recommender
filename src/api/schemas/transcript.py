"""Schema Pydantic cho luồng bảng điểm sinh viên tự nhập theo hợp đồng mục 6.10, 6.11 và 6.7."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError, ValidationError

from src.api.schemas.recommendations import RecommendationItemOut
from src.api.schemas.students import (
    CourseStatusCode,
    CourseStatusSummaryOut,
    StatusBlockDetailOut,
    StudentProfileBlockOut,
)

NotSelectedReasonCode = Literal["skipped", "block_full", "credit_budget"]
WarningCode = Literal[
    "below_min_credits",
    "prerequisite_not_in_transcript",
    "studied_before_prerequisite",
]


def _reject_bool_number(value: Any, error_type: str, message: str) -> Any:
    """Từ chối giá trị boolean cho trường số để tránh `true`/`false` bị ép thành `1`/`0`."""
    if isinstance(value, bool):
        raise PydanticCustomError(error_type, message)
    return value


class TranscriptResultIn(BaseModel):
    """Một dòng kết quả học tập trong bảng điểm tự nhập (mục 6.10)."""

    model_config = ConfigDict(extra="forbid")

    course_code: str = Field(..., min_length=1)
    semester: int = Field(..., ge=1)
    score: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    exempted: bool | None = Field(default=None)

    @field_validator("semester", mode="before")
    @classmethod
    def _validate_semester_not_bool(cls, value: Any) -> Any:
        return _reject_bool_number(value, "int_type", "Học kỳ phải là số nguyên, không phải kiểu boolean.")

    @field_validator("score", mode="before")
    @classmethod
    def _validate_score_not_bool(cls, value: Any) -> Any:
        return _reject_bool_number(value, "float_type", "Điểm phải là số, không phải kiểu boolean.")

    @model_validator(mode="after")
    def _check_score_or_exempted(self) -> TranscriptResultIn:
        """Mỗi dòng kết quả chỉ được truyền đúng một trong hai: `score` hoặc `exempted=true` (§6.10)."""
        if self.exempted is True:
            if self.score is not None:
                raise ValidationError.from_exception_data(
                    title=self.__class__.__name__,
                    line_errors=[
                        InitErrorDetails(
                            type=PydanticCustomError(
                                "score_and_exempted",
                                "Không được truyền cả score và exempted=true trong cùng một dòng kết quả.",
                            ),
                            loc=("score",),
                            input=self.score,
                        )
                    ],
                )
        else:
            if self.score is None:
                raise ValidationError.from_exception_data(
                    title=self.__class__.__name__,
                    line_errors=[
                        InitErrorDetails(
                            type=PydanticCustomError(
                                "missing_score_or_exempted",
                                "Mỗi dòng kết quả phải có score hoặc exempted=true.",
                            ),
                            loc=("score",),
                            input=self.score,
                        )
                    ],
                )
            # Chuẩn hóa exempted=False về None để tầng luật chỉ nhận đúng một trong hai trường.
            self.exempted = None
        return self

    def to_rule_dict(self) -> dict[str, Any]:
        """Chuyển sang dict sạch (`course_code`, `semester`, và đúng một trong `score`/`exempted`)."""
        return self.model_dump(exclude_none=True)


class TranscriptIn(BaseModel):
    """Body đầu vào cho POST /v1/universities/{uni}/curricula/{curriculum_code}/transcript (mục 6.10)."""

    model_config = ConfigDict(extra="forbid")

    semesters_completed: int = Field(..., ge=0, le=12)
    results: list[TranscriptResultIn] = Field(default_factory=list, max_length=200)

    @field_validator("semesters_completed", mode="before")
    @classmethod
    def _validate_semesters_not_bool(cls, value: Any) -> Any:
        return _reject_bool_number(value, "int_type", "semesters_completed phải là số nguyên, không phải kiểu boolean.")


class TranscriptWarningOut(BaseModel):
    """Một cảnh báo cho bảng điểm tự nhập hoặc lượt gợi ý (mục 4.7)."""

    code: WarningCode
    course_code: str | None = None
    text: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class TranscriptLastAttemptOut(BaseModel):
    """Thông tin lần học gần nhất từ bảng điểm tự nhập (mục 6.10)."""

    semester: int
    score: float | None = None
    letter_grade: str | None = None


class TranscriptCourseStatusItemOut(BaseModel):
    """Trạng thái một học phần tính từ bảng điểm tự nhập (mục 6.10 và 6.11)."""

    course_code: str
    course_name: str
    credits: int
    block_code: str
    status: CourseStatusCode
    missing_prerequisites: list[list[str]] | None = None
    block: StatusBlockDetailOut | None = None
    last_attempt: TranscriptLastAttemptOut | None = None
    text: str | None = None


class TranscriptOut(BaseModel):
    """Phản hồi tiến độ và trạng thái học phần từ bảng điểm tự nhập (mục 6.10)."""

    university_code: str
    curriculum_code: str
    semesters_completed: int
    target_semester: int
    credits_earned: int
    credits_outstanding: int
    total_credits: int
    gpa: float | None = None
    max_credits_per_term: int
    outstanding_courses: list[str] = Field(default_factory=list)
    blocks: list[StudentProfileBlockOut] = Field(default_factory=list)
    summary: CourseStatusSummaryOut
    courses: list[TranscriptCourseStatusItemOut]
    warnings: list[TranscriptWarningOut] = Field(default_factory=list)


def _validate_credit_window_order(
    model_name: str, min_credits: int, max_credits: int | None
) -> int:
    """Áp dụng mặc định `max_credits = max(20, min_credits)` và báo lỗi ở `min_credits` nếu `min_credits > max_credits`."""
    if max_credits is None:
        return max(20, min_credits)
    if min_credits > max_credits:
        raise ValidationError.from_exception_data(
            title=model_name,
            line_errors=[
                InitErrorDetails(
                    type=PydanticCustomError(
                        "credit_window_order",
                        "min_credits không được lớn hơn max_credits.",
                    ),
                    loc=("min_credits",),
                    input=min_credits,
                )
            ],
        )
    return max_credits


class TranscriptRecommendationIn(TranscriptIn):
    """Body đầu vào cho POST /v1/universities/{uni}/curricula/{curriculum_code}/recommendations (mục 6.11).

    Không nhận `limit`, `assumptions`, `swap` (extra='forbid' tự từ chối với 422 validation_error).
    """

    model_config = ConfigDict(extra="forbid")

    min_credits: int = Field(default=10, ge=10, le=40)
    max_credits: int | None = Field(default=None, ge=10, le=40)
    skip: list[str] = Field(default_factory=list)
    include: list[str] = Field(default_factory=list)
    weights: dict[str, float] | None = Field(default=None)

    @field_validator("min_credits", mode="before")
    @classmethod
    def _validate_min_credits_not_bool(cls, value: Any) -> Any:
        return _reject_bool_number(value, "int_type", "min_credits phải là số nguyên, không phải kiểu boolean.")

    @field_validator("max_credits", mode="before")
    @classmethod
    def _validate_max_credits_not_bool(cls, value: Any) -> Any:
        return _reject_bool_number(value, "int_type", "max_credits phải là số nguyên, không phải kiểu boolean.")

    @model_validator(mode="after")
    def _check_credit_window(self) -> TranscriptRecommendationIn:
        self.max_credits = _validate_credit_window_order(self.__class__.__name__, self.min_credits, self.max_credits)
        return self


class CreditWindowOut(BaseModel):
    """Khoảng tín chỉ sinh viên đặt và tổng tín chỉ thực tế được xếp (mục 6.11)."""

    min_credits: int
    max_credits: int
    total_credits: int
    text: str


class NotSelectedCourseOut(BaseModel):
    """Học phần học được nhưng không được xếp vào học kỳ gợi ý (mục 4.6 và 6.11)."""

    course_code: str
    course_name: str
    credits: int
    block_code: str
    status: Literal["retake", "eligible"]
    score: float
    reason: NotSelectedReasonCode
    text: str
    data: dict[str, Any] = Field(default_factory=dict)


class TranscriptRecommendationsOut(BaseModel):
    """Phản hồi gợi ý học phần theo khoảng tín chỉ từ bảng điểm tự nhập (mục 6.11)."""

    university_code: str
    curriculum_code: str
    algorithm_version: str
    what_if: bool
    weights: dict[str, float]
    target_semester: int
    credit_window: CreditWindowOut
    candidate_count: int
    items: list[RecommendationItemOut] = Field(default_factory=list)
    not_selected: list[NotSelectedCourseOut] = Field(default_factory=list)
    not_eligible: list[TranscriptCourseStatusItemOut] = Field(default_factory=list)
    warnings: list[TranscriptWarningOut] = Field(default_factory=list)
