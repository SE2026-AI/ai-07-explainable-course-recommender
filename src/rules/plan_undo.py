"""
Module quản lý thao tác xóa học phần khỏi kế hoạch học kỳ và khôi phục (Undo) - Biến thể VT-097.
Phiên bản Baseline Stub (trước khi áp dụng AI Minimal Patch):
- Đã có khung lưu/khôi phục cơ bản trên bộ nhớ cho happy path,
- Chưa chuẩn hóa .strip() và chưa kiểm tra biên độ dài [3..16], biên số lượng [1..10],
- Chưa kiểm tra trần tín chỉ max_credits_per_term (24 TC), biên TTL 300s, consumed và authorization.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

MAX_BATCH_REMOVE = 10
UNDO_TTL_SECONDS = 300.0


class PlanUndoValidationError(ValueError):
    """Lỗi khi dữ liệu biên hoặc rỗng vi phạm quy tắc validation (HTTP 422)."""


class PlanUndoAuthError(PermissionError):
    """Lỗi khi người gọi không có quyền sở hữu đối với kế hoạch học kỳ (HTTP 403)."""


class PlanUndoConflictError(RuntimeError):
    """Lỗi khi thao tác Undo không khả dụng, đã dùng hoặc hết hạn (HTTP 409)."""


@dataclass(frozen=True)
class PlannedCourse:
    course_code: str
    credits: int


@dataclass
class UndoSnapshot:
    undo_token: str
    university_code: str
    student_code: str
    term_code: str
    removed_courses: list[PlannedCourse]
    created_at: float
    expires_at: float
    consumed: bool = False


class PlanUndoService:
    """Service quản lý xóa học phần dự kiến và hoàn tác (Undo) trên kế hoạch học kỳ."""

    def __init__(self, clock_fn: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock_fn
        self._plans: dict[tuple[str, str, str], dict[str, PlannedCourse]] = {}
        self._max_credits: dict[tuple[str, str, str], int] = {}
        self._latest_snapshot: dict[tuple[str, str, str], UndoSnapshot] = {}
        self._snapshots_by_token: dict[str, UndoSnapshot] = {}

    def seed_plan(
        self,
        university_code: str,
        student_code: str,
        term_code: str,
        courses: list[dict[str, Any]],
        max_credits_per_term: int = 24,
    ) -> None:
        key = (university_code, student_code, term_code)
        self._plans[key] = {
            str(c["course_code"]): PlannedCourse(str(c["course_code"]), int(c["credits"]))
            for c in courses
        }
        self._max_credits[key] = int(max_credits_per_term)

    def total_credits(self, university_code: str, student_code: str, term_code: str) -> int:
        key = (university_code, student_code, term_code)
        return sum(c.credits for c in self._plans.get(key, {}).values())

    def remove_planned_courses(
        self,
        university_code: str,
        student_code: str,
        term_code: str,
        course_codes: list[str],
        actor_student_code: str,
    ) -> dict[str, Any]:
        key = (university_code, student_code, term_code)
        plan = self._plans.setdefault(key, {})
        removed = [plan.pop(code) for code in course_codes if code in plan]
        now = self._clock()
        token = f"undo-{uuid.uuid4().hex[:12]}"
        snap = UndoSnapshot(
            undo_token=token,
            university_code=university_code,
            student_code=student_code,
            term_code=term_code,
            removed_courses=removed,
            created_at=now,
            expires_at=now + UNDO_TTL_SECONDS,
        )
        self._latest_snapshot[key] = snap
        self._snapshots_by_token[token] = snap
        return {
            "university_code": university_code,
            "student_code": student_code,
            "term": term_code,
            "undo_token": token,
            "removed_count": len(removed),
            "remaining_credits": self.total_credits(university_code, student_code, term_code),
        }

    def undo_last_removal(
        self,
        university_code: str,
        student_code: str,
        term_code: str,
        actor_student_code: str,
        undo_token: str | None = None,
    ) -> dict[str, Any]:
        key = (university_code, student_code, term_code)
        snap = self._snapshots_by_token.get(undo_token) if undo_token else self._latest_snapshot.get(key)
        if not snap:
            raise PlanUndoConflictError("Không có thao tác xóa nào để hoàn tác.")
        plan = self._plans.setdefault(key, {})
        for c in snap.removed_courses:
            plan[c.course_code] = c
        return {
            "university_code": university_code,
            "student_code": student_code,
            "term": term_code,
            "restored_codes": [c.course_code for c in snap.removed_courses],
            "total_credits": self.total_credits(university_code, student_code, term_code),
        }
