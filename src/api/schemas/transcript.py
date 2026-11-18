"""Schema Pydantic cho luồng bảng điểm sinh viên tự nhập theo hợp đồng mục 6.10."""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError, ValidationError

from src.api.schemas.students import (
    CourseStatusCode,
    CourseStatusSummaryOut,
    StatusBlockDetailOut,
    StudentProfileBlockOut,
)

WarningCode = Literal[
    "below_min_credits",
    "prerequisite_not_in_transcript",
    "studied_before_prerequisite",
]

# Kiểu số thực chặt: từ chối chuỗi "7.5" và boolean, nhưng vẫn nhận số nguyên JSON như 7.
_StrictFloat = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]


class TranscriptResultIn(BaseModel):
    """Một dòng kết quả học tập trong bảng điểm tự nhập (mục 6.10)."""

    model_config = ConfigDict(extra="forbid")

    course_code: StrictStr = Field(..., min_length=1, max_length=32)
    semester: StrictInt = Field(..., ge=1, le=12)
    score: _StrictFloat | None = None
    exempted: StrictBool | None = None

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

    semesters_completed: StrictInt = Field(..., ge=0, le=12)
    results: list[TranscriptResultIn] = Field(default_factory=list, max_length=200)


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
    """Trạng thái một học phần tính từ bảng điểm tự nhập (mục 6.10)."""

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
