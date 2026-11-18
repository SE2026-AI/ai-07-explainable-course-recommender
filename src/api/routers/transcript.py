"""Router cho luồng bảng điểm sinh viên tự nhập (stateless) theo hợp đồng mục 6.10."""
from __future__ import annotations

import importlib
import importlib.util
import logging
import math
import re
from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends

import src.rules.status
from src import explain
from src.api.deps import get_repo
from src.api.errors import ApiError
from src.api.schemas.common import ERROR_RESPONSES
from src.api.schemas.students import (
    CourseStatusSummaryOut,
    StatusBlockDetailOut,
    StudentProfileBlockOut,
)
from src.api.schemas.transcript import (
    TranscriptCourseStatusItemOut,
    TranscriptIn,
    TranscriptLastAttemptOut,
    TranscriptOut,
    TranscriptWarningOut,
)
from src.api.services.students import (
    filter_leaf_blocks,
    validate_curriculum,
    validate_university,
)
from src.api.stubs.transcript_contract import _CONTRACT_TRANSCRIPT_STUB
from src.data.repository import Repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bảng điểm tự nhập"])

# Thông điệp ValueError từ tầng rules mở đầu bằng đường dẫn trường kiểu JS (mục 5).
_TRANSCRIPT_FIELD_PATH = re.compile(
    r"^((?:results\[\d+\](?:\.\w+)?|semesters_completed)): (.+)$",
    re.DOTALL,
)


def _transcript_value_error(exc: ValueError) -> ApiError | None:
    """Chuyển `ValueError` có đường dẫn trường hợp lệ sang 422 `validation_error`; `None` nếu lỗi nội bộ."""
    matched = _TRANSCRIPT_FIELD_PATH.match(str(exc))
    if not matched:
        return None
    return ApiError(
        code="validation_error",
        message="Dữ liệu gửi lên không hợp lệ.",
        status=422,
        details={"fields": {matched.group(1): matched.group(2)}},
    )


def _load_build_student() -> Callable[..., Any] | None:
    """Tra cứu động `src.rules.transcript.build_student` (RULES-4); trả `None` nếu chưa merge.

    Dùng `find_spec` để phân biệt: module vắng → stub; module có nhưng lỗi import thật → nổ → 500.
    Khi module đã có trong sys.modules (ví dụ do monkeypatch trong test), kiểm trực tiếp sys.modules.
    """
    import sys

    if "src.rules.transcript" in sys.modules:
        module = sys.modules["src.rules.transcript"]
    else:
        try:
            spec = importlib.util.find_spec("src.rules.transcript")
        except ValueError:
            spec = None
        if spec is None:
            return None  # RULES-4 chưa merge: dùng stub
        module = importlib.import_module("src.rules.transcript")  # lỗi import thật phải nổ -> 500

    build = getattr(module, "build_student", None)
    if build is None:
        raise RuntimeError("src.rules.transcript thiếu build_student")
    return build


def _clean_float(value: Any) -> float | None:
    """Chuyển điểm sang float hoặc `None` nếu thiếu/NaN."""
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return None if math.isnan(number) else number


def _validate_stub_transcript(curriculum: pd.Series, courses_df: pd.DataFrame, body: TranscriptIn) -> None:
    """Kiểm tra ràng buộc đầu vào theo khung khi chạy ở chế độ Stub (chưa có `RULES-4`).

    Chỉ kiểm tra dữ liệu đầu vào (mã thuộc khung, không lặp, học kỳ <= semesters_completed,
    điểm <= max_score) và ném `ValueError` cùng định dạng đường dẫn trường như tầng luật.
    """
    valid_codes = set(courses_df["course_code"].astype(str))
    max_score = float(curriculum["max_score"])
    seen_codes: set[str] = set()

    for idx, item in enumerate(body.results):
        if item.course_code not in valid_codes:
            raise ValueError(f"results[{idx}].course_code: '{item.course_code}' không thuộc khung chương trình đào tạo.")
        if item.course_code in seen_codes:
            raise ValueError(f"results[{idx}].course_code: '{item.course_code}' đã xuất hiện ở dòng trước.")
        seen_codes.add(item.course_code)
        if item.semester > body.semesters_completed:
            raise ValueError(
                f"results[{idx}].semester: học kỳ {item.semester} vượt quá semesters_completed ({body.semesters_completed})."
            )
        if item.score is not None and item.score > max_score:
            raise ValueError(f"results[{idx}].score: điểm {item.score} vượt quá thang điểm tối đa {max_score:g} của khung.")


def _build_transcript_student(
    repo: Repository,
    uni: str,
    curriculum_code: str,
    curriculum: pd.Series,
    courses_df: pd.DataFrame,
    body: TranscriptIn,
) -> Mapping[str, Any] | None:
    """Gọi `build_student()` thật (RULES-4 + DATA-4). Trả `None` nếu tầng dưới chưa merge."""
    build_student = _load_build_student()
    if build_student is None or not hasattr(repo, "grade_conversions"):
        return None

    conversions = repo.grade_conversions(curriculum_code)
    results_dicts = [r.to_rule_dict() for r in body.results]
    try:
        student = build_student(curriculum, courses_df, conversions, body.semesters_completed, results_dicts)
    except ValueError as exc:
        api_err = _transcript_value_error(exc)
        if api_err is None:
            raise
        raise api_err from exc

    if isinstance(student, Mapping):
        student = dict(student)
        student.setdefault("student_id", None)
        student.setdefault("university_code", uni)
        student.setdefault("curriculum_code", curriculum_code)
    return student


def _build_transcript_course_status_item(
    course_row: pd.Series,
    detail: Mapping[str, Any],
    names: Mapping[str, str],
) -> TranscriptCourseStatusItemOut:
    """Dựng một phần tử `courses[]` của mục 6.10 từ hàng học phần và chi tiết trạng thái."""
    code = str(course_row["course_code"])
    status = detail["status"]

    item_kwargs: dict[str, Any] = {
        "course_code": code,
        "course_name": str(course_row["course_name"]),
        "credits": int(course_row["credits"]),
        "block_code": str(course_row["block_code"]),
        "status": status,
    }

    if status == "missing_prerequisite" and "missing_prerequisites" in detail:
        item_kwargs["missing_prerequisites"] = detail["missing_prerequisites"]
    elif status == "block_complete" and "block" in detail:
        block = detail["block"]
        item_kwargs["block"] = StatusBlockDetailOut(
            block_code=str(block["block_code"]),
            block_name=str(block["block_name"]),
            required_credits=int(block["required_credits"]),
            earned_credits=int(block["earned_credits"]),
        )
    elif status in ("passed", "retake") and detail.get("last_attempt") is not None:
        la = detail["last_attempt"]
        letter = la.get("letter_grade")
        item_kwargs["last_attempt"] = TranscriptLastAttemptOut(
            semester=int(la["semester"]),
            score=_clean_float(la.get("score")),
            letter_grade=None if (letter is None or pd.isna(letter)) else str(letter),
        )

    course_obj = {**course_row.to_dict(), "course_code": code}
    item_kwargs["text"] = detail["text"] if detail.get("text") is not None else explain.status_text(course_obj, detail, names)
    return TranscriptCourseStatusItemOut(**item_kwargs)


def _format_warnings(raw_warnings: Any, names: Mapping[str, str]) -> list[TranscriptWarningOut]:
    """Chuyển danh sách cảnh báo từ tầng luật/xếp hạng sang schema đầu ra (gọi `explain.warning_text`)."""
    warnings_out: list[TranscriptWarningOut] = []
    for warning in raw_warnings or []:
        text_val = warning.get("text")
        if text_val is None and hasattr(explain, "warning_text"):
            text_val = explain.warning_text(warning, names)
        warnings_out.append(
            TranscriptWarningOut(
                code=str(warning["code"]),  # type: ignore[arg-type]
                course_code=str(warning["course_code"]) if warning.get("course_code") is not None else None,
                text=text_val,
                data=dict(warning.get("data", {})),
            )
        )
    return warnings_out


def _extract_blocks(student: Mapping[str, Any]) -> list[StudentProfileBlockOut]:
    """Chuyển `student['blocks']` sang `list[StudentProfileBlockOut]` bằng helper chung (§6.4 và §6.10)."""
    return filter_leaf_blocks(student.get("blocks"))


def _run_transcript_pipeline(
    repo: Repository,
    uni: str,
    curriculum_code: str,
    curriculum: pd.Series,
    courses_df: pd.DataFrame,
    body: TranscriptIn,
) -> TranscriptOut:
    """Chạy luồng Live (`RULES-4`/`RULES-5`/`DATA-4`) hoặc Stub Fallback (§6.10) khi phụ thuộc chưa merge."""
    student = _build_transcript_student(repo, uni, curriculum_code, curriculum, courses_df, body)
    if student is None:
        try:
            _validate_stub_transcript(curriculum, courses_df, body)
        except ValueError as exc:
            api_err = _transcript_value_error(exc)
            if api_err is None:
                raise
            raise api_err from exc
        return TranscriptOut(
            university_code=uni,
            curriculum_code=curriculum_code,
            semesters_completed=body.semesters_completed,
            target_semester=body.semesters_completed + 1,
            total_credits=int(curriculum["total_credits"]),
            max_credits_per_term=int(curriculum["max_credits_per_term"]),
            **_CONTRACT_TRANSCRIPT_STUB,
        )

    status_details = src.rules.status.course_status_details(repo, student)
    sorted_courses = courses_df.sort_values(by="course_code")
    names = dict(zip(sorted_courses["course_code"].astype(str), sorted_courses["course_name"].astype(str), strict=True))

    courses_list: list[TranscriptCourseStatusItemOut] = []
    for _, row in sorted_courses.iterrows():
        c_code = str(row["course_code"])
        if c_code not in status_details:
            logger.error("course_status_details thiếu mã %s của khung %s", c_code, curriculum_code)
            raise ApiError(code="internal_error", message="Lỗi máy chủ nội bộ.", status=500, details={})
        courses_list.append(_build_transcript_course_status_item(row, status_details[c_code], names))

    counts = Counter(item.status for item in courses_list)
    summary = CourseStatusSummaryOut(
        passed=counts.get("passed", 0),
        retake=counts.get("retake", 0),
        eligible=counts.get("eligible", 0),
        missing_prerequisite=counts.get("missing_prerequisite", 0),
        block_complete=counts.get("block_complete", 0),
    )

    # GPA làm tròn 2 chữ số thập phân nếu tầng dưới không làm tròn sẵn (§6.10)
    gpa_val = _clean_float(student.get("gpa"))
    if gpa_val is not None:
        gpa_val = round(gpa_val, 2)

    outstanding = student.get("outstanding_courses")
    outstanding_list = [str(c) for c in outstanding] if isinstance(outstanding, (list, tuple)) else []

    return TranscriptOut(
        university_code=uni,
        curriculum_code=curriculum_code,
        semesters_completed=int(student.get("semesters_completed", body.semesters_completed)),
        target_semester=int(student.get("target_semester", body.semesters_completed + 1)),
        credits_earned=int(student["credits_earned"]),
        credits_outstanding=int(student["credits_outstanding"]),
        total_credits=int(curriculum["total_credits"]),
        gpa=gpa_val,
        max_credits_per_term=int(curriculum["max_credits_per_term"]),
        outstanding_courses=outstanding_list,
        blocks=_extract_blocks(student),
        summary=summary,
        courses=courses_list,
        warnings=_format_warnings(student.get("warnings"), names),
    )


@router.post(
    "/universities/{uni}/curricula/{curriculum_code}/transcript",
    response_model=TranscriptOut,
    summary="Tiến độ và trạng thái học phần từ bảng điểm tự nhập",
    description=(
        "Tính tiến độ tích lũy và trạng thái từng học phần của khung CTĐT trực tiếp từ bảng điểm trong body, "
        "không cần mã sinh viên và không lưu vào cơ sở dữ liệu (mục 6.10)."
    ),
    responses={**ERROR_RESPONSES},
)
def post_curriculum_transcript(
    uni: str,
    curriculum_code: str,
    body: TranscriptIn,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> TranscriptOut:
    """POST /v1/universities/{uni}/curricula/{curriculum_code}/transcript (mục 6.10)."""
    validate_university(repo, uni)
    validate_curriculum(repo, uni, curriculum_code)

    curriculum = repo.curriculum(curriculum_code)
    courses_df = repo.curriculum_courses(curriculum_code)
    return _run_transcript_pipeline(repo, uni, curriculum_code, curriculum, courses_df, body)
