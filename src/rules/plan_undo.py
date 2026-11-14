"""
Module quản lý thao tác xóa học phần khỏi kế hoạch học kỳ và khôi phục (Undo) - Biến thể VT-097.
Phiên bản sau khi áp dụng AI Minimal Patch (khớp kiến trúc main@30fd287):
- Chuẩn hóa .strip() và kiểm tra biên độ dài [3..16], chặn chuỗi rỗng/khoảng trắng (Risk VT-097).
- Kiểm tra biên số lượng môn xóa N in [1..10] (Boundary Value Analysis).
- Kiểm tra quyền sở hữu (actor_student_code == student_code) trên cả 2 đường đi hoàn tác.
- Bảo vệ Invariant trần tín chỉ học kỳ (max_credits_per_term = 24), TTL 300.0s và tính đơn nhất (consumed).
"""
from __future__ import annotations

import re
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

MIN_COURSE_CREDITS = 1
MAX_COURSE_CREDITS = 24
MIN_BATCH_REMOVE = 1
MAX_BATCH_REMOVE = 10
MIN_CODE_LEN = 3
MAX_CODE_LEN = 16
UNDO_TTL_SECONDS = 300.0
COURSE_CODE_PATTERN = re.compile(r"^[A-Z0-9_\-]+$")


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


def _validate_identifier(value: str, field_name: str, min_len: int = 2, max_len: int = 20) -> str:
    if not isinstance(value, str):
        raise PlanUndoValidationError(f"Trường '{field_name}' phải là chuỗi ký tự.")
    cleaned = value.strip()
    if len(cleaned) < min_len or len(cleaned) > max_len:
        raise PlanUndoValidationError(
            f"Độ dài '{field_name}' sau khi strip phải thuộc đoạn [{min_len}, {max_len}], nhận {len(cleaned)}."
        )
    return cleaned


def _validate_course_code(code: str) -> str:
    cleaned = _validate_identifier(code, "course_code", MIN_CODE_LEN, MAX_CODE_LEN)
    if not COURSE_CODE_PATTERN.match(cleaned):
        raise PlanUndoValidationError(f"Mã học phần '{cleaned}' chứa ký tự không hợp lệ.")
    return cleaned


class PlanUndoService:
    """Service quản lý xóa học phần dự kiến và hoàn tác (Undo) trên kế hoạch học kỳ."""

    def __init__(self, clock_fn: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock_fn
        self._lock = threading.RLock()
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
        clean_uni = _validate_identifier(university_code, "university_code", 2, 16)
        clean_student = _validate_identifier(student_code, "student_code", 3, 20)
        clean_term = _validate_identifier(term_code, "term_code", 4, 10)
        key = (clean_uni, clean_student, clean_term)
        with self._lock:
            plan_map: dict[str, PlannedCourse] = {}
            for c in courses:
                code = _validate_course_code(str(c["course_code"]))
                credits = int(c["credits"])
                if credits < MIN_COURSE_CREDITS or credits > MAX_COURSE_CREDITS:
                    raise PlanUndoValidationError(f"Số tín chỉ không hợp lệ: {credits}")
                plan_map[code] = PlannedCourse(code, credits)
            self._plans[key] = plan_map
            self._max_credits[key] = int(max_credits_per_term)

    def total_credits(self, university_code: str, student_code: str, term_code: str) -> int:
        key = (university_code.strip(), student_code.strip(), term_code.strip())
        with self._lock:
            return sum(c.credits for c in self._plans.get(key, {}).values())

    def remove_planned_courses(
        self,
        university_code: str,
        student_code: str,
        term_code: str,
        course_codes: list[str],
        actor_student_code: str,
    ) -> dict[str, Any]:
        clean_uni = _validate_identifier(university_code, "university_code", 2, 16)
        clean_student = _validate_identifier(student_code, "student_code", 3, 20)
        clean_term = _validate_identifier(term_code, "term_code", 4, 10)
        clean_actor = _validate_identifier(actor_student_code, "actor_student_code", 3, 20)

        if clean_actor != clean_student:
            raise PlanUndoAuthError("Sinh viên không có quyền xóa kế hoạch học tập của người khác.")

        if not isinstance(course_codes, list) or not (
            MIN_BATCH_REMOVE <= len(course_codes) <= MAX_BATCH_REMOVE
        ):
            raise PlanUndoValidationError(
                f"Số lượng học phần xóa một lần phải thuộc đoạn [{MIN_BATCH_REMOVE}, {MAX_BATCH_REMOVE}]."
            )

        normalized_codes: list[str] = []
        seen: set[str] = set()
        for raw_code in course_codes:
            code = _validate_course_code(raw_code)
            if code in seen:
                raise PlanUndoValidationError(f"Mã học phần bị lặp trong yêu cầu xóa: {code}.")
            seen.add(code)
            normalized_codes.append(code)

        key = (clean_uni, clean_student, clean_term)
        with self._lock:
            plan = self._plans.get(key)
            if not plan:
                raise PlanUndoConflictError("Kế hoạch học kỳ đang trống hoặc chưa khởi tạo.")

            missing = [c for c in normalized_codes if c not in plan]
            if missing:
                raise PlanUndoValidationError(f"Học phần không có trong kế hoạch hiện tại: {missing}.")

            removed = [plan.pop(c) for c in normalized_codes]
            now = self._clock()
            token = f"undo-{uuid.uuid4().hex[:12]}"
            snap = UndoSnapshot(
                undo_token=token,
                university_code=clean_uni,
                student_code=clean_student,
                term_code=clean_term,
                removed_courses=removed,
                created_at=now,
                expires_at=now + UNDO_TTL_SECONDS,
                consumed=False,
            )
            self._latest_snapshot[key] = snap
            self._snapshots_by_token[token] = snap
            remaining = sum(c.credits for c in plan.values())

        return {
            "university_code": clean_uni,
            "student_code": clean_student,
            "term": clean_term,
            "undo_token": token,
            "removed_count": len(removed),
            "remaining_credits": remaining,
        }

    def undo_last_removal(
        self,
        university_code: str,
        student_code: str,
        term_code: str,
        actor_student_code: str,
        undo_token: str | None = None,
    ) -> dict[str, Any]:
        clean_uni = _validate_identifier(university_code, "university_code", 2, 16)
        clean_student = _validate_identifier(student_code, "student_code", 3, 20)
        clean_term = _validate_identifier(term_code, "term_code", 4, 10)
        clean_actor = _validate_identifier(actor_student_code, "actor_student_code", 3, 20)
        key = (clean_uni, clean_student, clean_term)

        with self._lock:
            # Đường đi 1: Quick-Undo không truyền undo_token (lấy bản chụp gần nhất của học kỳ)
            if undo_token is None:
                if clean_actor != clean_student:
                    raise PlanUndoAuthError("Không có quyền hoàn tác nhanh trên kế hoạch của SV khác.")
                snap = self._latest_snapshot.get(key)
            else:
                # Đường đi 2: Hoàn tác theo mã undo_token tường minh
                clean_token = _validate_identifier(undo_token, "undo_token", 6, 40)
                snap = self._snapshots_by_token.get(clean_token)
                if snap is None:
                    raise PlanUndoConflictError("Không tìm thấy undo_token.")
                if clean_actor != snap.student_code or snap.student_code != clean_student:
                    raise PlanUndoAuthError('Không có quyền hoàn tác bằng undo_token của SV khác.')

            if snap is None or snap.term_code != clean_term or snap.university_code != clean_uni:
                raise PlanUndoConflictError("Không có thao tác xóa nào khả dụng để hoàn tác.")

            if snap.consumed:
                raise PlanUndoConflictError("Thao tác hoàn tác này đã được thực hiện trước đó.")

            now = self._clock()
            if now - snap.created_at > UNDO_TTL_SECONDS or now > snap.expires_at:
                raise PlanUndoConflictError("Đã quá thời hạn hoàn tác (300 giây).")

            plan = self._plans.setdefault(key, {})
            max_credits = self._max_credits.get(key, 24)
            current_credits = sum(c.credits for c in plan.values())
            restored_credits = sum(
                c.credits for c in snap.removed_courses if c.course_code not in plan
            )
            if current_credits + restored_credits > max_credits:
                raise PlanUndoValidationError(
                    f"credit_limit_exceeded: Tổng tín chỉ ({current_credits + restored_credits}) vượt trần ({max_credits})."
                )

            for c in snap.removed_courses:
                plan[c.course_code] = c

            snap.consumed = True
            total_after = sum(c.credits for c in plan.values())

        return {
            "university_code": clean_uni,
            "student_code": clean_student,
            "term": clean_term,
            "restored_codes": [c.course_code for c in snap.removed_courses],
            "total_credits": total_after,
        }
