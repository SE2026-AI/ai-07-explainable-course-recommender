"""Router cho luồng bảng điểm sinh viên tự nhập (stateless) theo hợp đồng mục 6.10 và 6.11."""
from __future__ import annotations

import logging
import math
import re
from collections.abc import Mapping
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends

import src.recommender
import src.rules.status
from src import explain
from src.api.deps import get_repo
from src.api.errors import ApiError
from src.api.schemas.common import ERROR_RESPONSES
from src.api.schemas.students import StatusBlockDetailOut, StudentProfileBlockOut
from src.api.schemas.transcript import (
    TranscriptCourseStatusItemOut,
    TranscriptIn,
    TranscriptLastAttemptOut,
    TranscriptOut,
    TranscriptRecommendationIn,
    TranscriptRecommendationsOut,
    TranscriptWarningOut,
)
from src.api.services.students import (
    filter_leaf_blocks,
    summarize_course_status,
    validate_curriculum,
    validate_university,
)
from src.data.repository import Repository
from src.recommender.scoring import merge_weights
from src.rules.transcript import build_student

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bảng điểm tự nhập"])

# Thông điệp ValueError từ tầng rules / recommender mở đầu bằng đường dẫn trường kiểu JS (mục 5).
_TRANSCRIPT_FIELD_PATH = re.compile(
    r"^((?:results\[\d+\](?:\.\w+)?|semesters_completed|include(?:\[\d+\])?|skip(?:\[\d+\])?|"
    r"min_credits|max_credits|weights(?:\.\w+)?|course_codes(?:\[\d+\])?)): (.+)$",
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


def _clean_float(value: Any) -> float | None:
    """Chuyển điểm sang float hoặc `None` nếu thiếu/NaN."""
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return None if math.isnan(number) else number


def _build_transcript_student(
    repo: Repository,
    uni: str,
    curriculum_code: str,
    curriculum: pd.Series,
    courses_df: pd.DataFrame,
    body: TranscriptIn,
) -> Mapping[str, Any]:
    """Gọi `build_student()` (RULES-4 + DATA-4); `ValueError` có đường dẫn trường thành 422 `validation_error`."""
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
    """Chạy luồng tính tiến độ và trạng thái học phần (`RULES-4`/`RULES-5`/`DATA-4`, §6.10)."""
    student = _build_transcript_student(repo, uni, curriculum_code, curriculum, courses_df, body)
    status_details = src.rules.status.course_status_details(repo, student)
    # `course_status_details` ghi `last_attempt` theo term_code; bảng điểm tự nhập chỉ có học kỳ (semester).
    for code, attempt in (student.get("latest_attempts") or {}).items():
        last_attempt = status_details.get(code, {}).get("last_attempt")
        if last_attempt is not None:
            last_attempt["semester"] = attempt["semester"]
    sorted_courses = courses_df.sort_values(by="course_code")
    names = dict(zip(sorted_courses["course_code"].astype(str), sorted_courses["course_name"].astype(str), strict=True))

    courses_list: list[TranscriptCourseStatusItemOut] = []
    for _, row in sorted_courses.iterrows():
        c_code = str(row["course_code"])
        if c_code not in status_details:
            logger.error("course_status_details thiếu mã %s của khung %s", c_code, curriculum_code)
            raise ApiError(code="internal_error", message="Lỗi máy chủ nội bộ.", status=500, details={})
        courses_list.append(_build_transcript_course_status_item(row, status_details[c_code], names))

    summary = summarize_course_status(item.status for item in courses_list)

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
        gpa=_clean_float(student.get("gpa")),
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


def _validate_and_merge_weights(weights: dict[str, float] | None) -> dict[str, float] | None:
    """Ghép trọng số bằng `merge_weights()`; lỗi gắn khóa `weights.<mã>` theo từng trọng số (mục 5).

    Mọi quy tắc kiểm tra nằm ở `merge_weights()`: router chỉ chạy lại hàm đó cho từng khóa để biết khóa nào sai.
    """
    if weights is None:
        return None
    try:
        return merge_weights(weights)
    except ValueError as exc:
        fields: dict[str, str] = {}
        for key, value in weights.items():
            try:
                merge_weights({key: value})
            except ValueError as key_exc:
                fields[f"weights.{key}"] = str(key_exc)
        raise ApiError(
            code="validation_error",
            message="Dữ liệu gợi ý không hợp lệ.",
            status=422,
            details={"fields": fields or {"weights": str(exc)}},
        ) from exc


def _run_recommendation_pipeline(
    repo: Repository,
    uni: str,
    curriculum_code: str,
    curriculum: pd.Series,
    courses_df: pd.DataFrame,
    body: TranscriptRecommendationIn,
) -> TranscriptRecommendationsOut:
    """Chạy luồng gợi ý từ bảng điểm tự nhập (`RULES-4`/`DATA-4`/`RANK-3`/`EXPLAIN-2`, §6.11)."""
    merged_weights = _validate_and_merge_weights(body.weights)
    student = _build_transcript_student(repo, uni, curriculum_code, curriculum, courses_df, body)

    try:
        rec: dict[str, Any] = src.recommender.recommend(
            repo,
            student,
            weights=merged_weights,
            skip=list(body.skip) or None,
            include=list(body.include) or None,
            min_credits=body.min_credits,
            max_credits=body.max_credits,  # None: recommend() tự tính mặc định và trả lại trong credit_window
        )
    except ValueError as exc:
        api_err = _transcript_value_error(exc)
        if api_err is None:
            raise
        raise api_err from exc

    # `recommend()` ghi `last_attempt` theo term_code; bảng điểm tự nhập chỉ có học kỳ (semester).
    attempts = student.get("latest_attempts") or {}
    for item in rec.get("not_eligible", []):
        last_attempt = item.get("last_attempt")
        if last_attempt is not None and item.get("course_code") in attempts:
            last_attempt["semester"] = attempts[item["course_code"]]["semester"]

    return TranscriptRecommendationsOut(
        university_code=uni,
        curriculum_code=curriculum_code,
        algorithm_version=src.recommender.ALGORITHM_VERSION,
        **rec,
    )


@router.post(
    "/universities/{uni}/curricula/{curriculum_code}/recommendations",
    response_model=TranscriptRecommendationsOut,
    summary="Gợi ý học phần theo khoảng tín chỉ từ bảng điểm tự nhập",
    description=(
        "Gợi ý danh sách học phần cho kỳ kế tiếp trong khoảng tín chỉ [min_credits, max_credits] trực tiếp từ "
        "bảng điểm trong body, kèm not_selected, not_eligible và warnings (mục 6.11)."
    ),
    responses={**ERROR_RESPONSES},
)
def post_curriculum_recommendations(
    uni: str,
    curriculum_code: str,
    body: TranscriptRecommendationIn,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> TranscriptRecommendationsOut:
    """POST /v1/universities/{uni}/curricula/{curriculum_code}/recommendations (mục 6.11)."""
    validate_university(repo, uni)
    validate_curriculum(repo, uni, curriculum_code)

    curriculum = repo.curriculum(curriculum_code)
    courses_df = repo.curriculum_courses(curriculum_code)
    return _run_recommendation_pipeline(repo, uni, curriculum_code, curriculum, courses_df, body)
