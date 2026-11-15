"""
Router cho thao tác xóa học phần dự kiến và hoàn tác (Undo) theo chuẩn hợp đồng API v1 (main@30fd287).
Sử dụng lớp ApiError chuẩn của dự án từ src/api/errors.py.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict, Field

from src.api.errors import ApiError
from src.rules.plan_undo import (
    PlanUndoAuthError,
    PlanUndoConflictError,
    PlanUndoService,
    PlanUndoValidationError,
)

router = APIRouter(tags=["Gợi ý & Kế hoạch - Undo (VT-097)"])
undo_service = PlanUndoService()


class PlanRemoveBodyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    term: str = Field(default="20261", description="Mã học kỳ (mặc định 20261)")
    course_codes: list[str] = Field(default_factory=list, description="Danh sách mã học phần cần bỏ")


class PlanUndoBodyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    term: str = Field(default="20261", description="Mã học kỳ (mặc định 20261)")
    undo_token: str | None = Field(default=None, description="Token hoàn tác (None nếu Quick-Undo)")


@router.post("/universities/{uni}/students/{student_code}/plan/remove")
def post_plan_remove(
    uni: str,
    student_code: str,
    body: PlanRemoveBodyIn,
    x_actor_student_code: str = Header(default="", alias="X-Actor-Student-Code"),
) -> dict[str, Any]:
    try:
        return undo_service.remove_planned_courses(
            university_code=uni,
            student_code=student_code,
            term_code=body.term,
            course_codes=body.course_codes,
            actor_student_code=x_actor_student_code,
        )
    except PlanUndoAuthError as exc:
        raise ApiError(code="forbidden_plan_access", message=str(exc), status=403) from exc
    except PlanUndoValidationError as exc:
        raise ApiError(code="validation_error", message=str(exc), status=422) from exc
    except PlanUndoConflictError as exc:
        raise ApiError(code="undo_conflict", message=str(exc), status=409) from exc


@router.post("/universities/{uni}/students/{student_code}/plan/undo")
def post_plan_undo(
    uni: str,
    student_code: str,
    body: PlanUndoBodyIn,
    x_actor_student_code: str = Header(default="", alias="X-Actor-Student-Code"),
) -> dict[str, Any]:
    try:
        return undo_service.undo_last_removal(
            university_code=uni,
            student_code=student_code,
            term_code=body.term,
            actor_student_code=x_actor_student_code,
            undo_token=body.undo_token,
        )
    except PlanUndoAuthError as exc:
        raise ApiError(code="forbidden_plan_access", message=str(exc), status=403) from exc
    except PlanUndoValidationError as exc:
        raise ApiError(code="validation_error", message=str(exc), status=422) from exc
    except PlanUndoConflictError as exc:
        raise ApiError(code="undo_conflict", message=str(exc), status=409) from exc
