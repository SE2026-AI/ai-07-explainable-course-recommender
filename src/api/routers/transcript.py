"""Router cho luồng bảng điểm sinh viên tự nhập (stateless) theo hợp đồng mục 6.10, 6.11 và 6.7."""
from __future__ import annotations

import inspect
import logging
import math
import re
from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends

import src.recommender
import src.rules.plan
import src.rules.status
from src import explain
from src.api.deps import get_repo
from src.api.errors import ApiError
from src.api.schemas.common import ERROR_RESPONSES
from src.api.schemas.recommendations import PlanViolationOut
from src.api.schemas.students import (
    CourseStatusSummaryOut,
    StatusBlockDetailOut,
    StudentProfileBlockOut,
)
from src.api.schemas.transcript import (
    CreditWindowOut,
    TranscriptCourseStatusItemOut,
    TranscriptIn,
    TranscriptLastAttemptOut,
    TranscriptOut,
    TranscriptPlanCheckIn,
    TranscriptPlanCheckOut,
    TranscriptRecommendationIn,
    TranscriptRecommendationsOut,
    TranscriptWarningOut,
)
from src.api.services.students import validate_curriculum, validate_university
from src.data.repository import Repository
from src.recommender.scoring import DEFAULT_WEIGHTS, merge_weights

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bảng điểm tự nhập"])

# Thông điệp ValueError từ tầng rules / recommender mở đầu bằng đường dẫn trường kiểu JS (mục 5).
_TRANSCRIPT_FIELD_PATH = re.compile(
    r"^((?:results\[\d+\](?:\.\w+)?|semesters_completed|include(?:\[\d+\])?|skip(?:\[\d+\])?|"
    r"min_credits|max_credits|weights(?:\.\w+)?|course_codes(?:\[\d+\])?)): (.+)$",
    re.DOTALL,
)

# Phản hồi mẫu nguyên văn từ hợp đồng §6.10, chỉ dùng làm Stub Fallback khi RULES-4/DATA-4 chưa merge.
_CONTRACT_TRANSCRIPT_STUB: dict[str, Any] = {
    "credits_earned": 34,
    "credits_outstanding": 3,
    "gpa": 2.76,
    "outstanding_courses": ["MAT2505"],
    "blocks": [
        {"block_code": "I.1", "required_credits": 16, "earned_credits": 8, "counts_toward_total": True},
        {"block_code": "I.2", "required_credits": 5, "earned_credits": 5, "counts_toward_total": True},
        {"block_code": "II", "required_credits": 5, "earned_credits": 2, "counts_toward_total": True},
        {"block_code": "IV", "required_credits": 28, "earned_credits": 13, "counts_toward_total": True},
        {"block_code": "V.1", "required_credits": 49, "earned_credits": 6, "counts_toward_total": True},
    ],
    "summary": {"passed": 10, "retake": 1, "eligible": 15, "missing_prerequisite": 33, "block_complete": 6},
    "courses": [
        {
            "course_code": "MAT2505",
            "course_name": "Lập trình cơ bản",
            "credits": 3,
            "block_code": "III",
            "status": "retake",
            "last_attempt": {"semester": 2, "score": 3.0, "letter_grade": "F"},
            "text": "Cần học lại Lập trình cơ bản: bạn chưa đạt môn này ở kỳ 2 (điểm 3,0).",
        },
        {
            "course_code": "PHI1006",
            "course_name": "Triết học Mác - Lênin",
            "credits": 3,
            "block_code": "I.1",
            "status": "passed",
            "last_attempt": {"semester": 1, "score": 7.5, "letter_grade": "B"},
            "text": "Đã đạt Triết học Mác - Lênin (điểm 7,5).",
        },
    ],
    "warnings": [],
}

# Phản hồi mẫu nguyên văn từ hợp đồng §6.11, chỉ dùng làm Stub Fallback khi RULES-4/DATA-4/RANK-3 chưa merge.
_CONTRACT_RECOMMENDATIONS_STUB: dict[str, Any] = {
    "credit_window_total": 20,
    "credit_window_text": "Tổng 20 tín chỉ, trong khoảng 15–20 bạn đặt.",
    "candidate_count": 16,
    "items": [
        {
            "rank": 1,
            "course_code": "MAT2505",
            "course_name": "Lập trình cơ bản",
            "credits": 3,
            "block_code": "III",
            "status": "retake",
            "score": 5.7083,
            "reasons": [
                {
                    "code": "outstanding_retake",
                    "contribution": 3.0,
                    "text": "Bạn chưa đạt môn này ở kỳ 2 (điểm 3,0).",
                    "data": {"semester": 2, "score": 3.0},
                },
                {
                    "code": "unlocks",
                    "contribution": 1.5,
                    "text": "Đạt môn này sẽ mở khóa 12 học phần khác của chương trình.",
                    "data": {
                        "count": 12,
                        "course_codes": [
                            "MAT1202", "MAT3373E", "MAT3505", "MAT3506", "MAT3507", "MAT3514",
                            "MAT3519", "MAT3539", "MAT3550E", "MAT3554E", "MAT3558", "MAT3560",
                        ],
                    },
                },
                {
                    "code": "overdue",
                    "contribution": 1.0,
                    "text": "Môn này dự kiến học ở kỳ 2, bạn đang ở kỳ 3.",
                    "data": {"recommended_semester": 2, "target_semester": 3, "semesters_late": 1},
                },
                {
                    "code": "strong_topic",
                    "contribution": 0.2083,
                    "text": "Bạn đang học tốt chủ đề Lập trình: điểm trung bình 5,3 trên 2 môn đã học.",
                    "data": {
                        "topic_code": "lap_trinh",
                        "topic_name": "Lập trình",
                        "average_score": 5.25,
                        "course_codes": ["HUS1011", "MAT2505"],
                    },
                },
            ],
        },
        {
            "rank": 7,
            "course_code": "MAT2407",
            "course_name": "Tối ưu hóa",
            "credits": 3,
            "block_code": "IV",
            "status": "eligible",
            "score": 0.5833,
            "reasons": [
                {
                    "code": "strong_topic",
                    "contribution": 0.5833,
                    "text": "Bạn đang học tốt chủ đề Toán: điểm trung bình 7,5 trên 4 môn đã học.",
                    "data": {
                        "topic_code": "toan",
                        "topic_name": "Toán",
                        "average_score": 7.5,
                        "course_codes": ["MAT2400", "MAT2501", "MAT2502", "MAT3500"],
                    },
                }
            ],
        },
    ],
    "not_selected": [
        {
            "course_code": "HUS1024",
            "course_name": "Nhập môn Robotic",
            "credits": 3,
            "block_code": "II",
            "status": "eligible",
            "score": 2.5833,
            "reason": "block_full",
            "text": (
                "Chưa xếp Nhập môn Robotic: khối kiến thức theo lĩnh vực chỉ cần 5 tín chỉ "
                "và đã có 5 từ môn đã đạt và môn xếp trên."
            ),
            "data": {
                "block_code": "II",
                "block_name": "Khối kiến thức theo lĩnh vực",
                "required_credits": 5,
                "taken_credits": 5,
                "credits": 3,
            },
        },
        {
            "course_code": "MAT2503",
            "course_name": "Giải tích 3",
            "credits": 2,
            "block_code": "IV",
            "status": "eligible",
            "score": 2.5833,
            "reason": "skipped",
            "text": "Bạn chọn chưa học Giải tích 3 ở kỳ này.",
            "data": {},
        },
        {
            "course_code": "MAT2403",
            "course_name": "Phương trình vi phân",
            "credits": 3,
            "block_code": "IV",
            "status": "eligible",
            "score": 0.7333,
            "reason": "credit_budget",
            "text": (
                "Chưa xếp Phương trình vi phân: kỳ này đã có 20 tín chỉ, "
                "thêm 3 tín chỉ sẽ vượt mức tối đa 20 bạn đặt."
            ),
            "data": {"credits": 3, "total_credits": 20, "max_credits": 20},
        },
    ],
    "not_eligible": [
        {
            "course_code": "MAT3533",
            "course_name": "Học máy",
            "credits": 3,
            "block_code": "V.1",
            "status": "missing_prerequisite",
            "missing_prerequisites": [["MAT2323"]],
            "text": "Chưa học được Học máy: cần hoàn thành Xác suất - Thống kê (MAT2323) trước.",
        }
    ],
    "warnings": [],
}


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
    """Tra cứu động `src.rules.transcript.build_student` (RULES-4); trả `None` nếu chưa merge."""
    try:
        from src.rules.transcript import build_student  # type: ignore[import-not-found]
    except ImportError:
        return None
    return build_student


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


def _extract_blocks(
    student: Mapping[str, Any],
    repo: Repository,
    curriculum_code: str,
    courses_df: pd.DataFrame,
) -> list[StudentProfileBlockOut]:
    """Chuyển `student['blocks']` hoặc tự tính từ `repo.blocks()` sang `list[StudentProfileBlockOut]` (§6.4 và §6.10)."""
    raw_blocks = student.get("blocks")
    if raw_blocks is not None:
        if isinstance(raw_blocks, pd.DataFrame):
            raw_blocks = raw_blocks.to_dict("records")
        blocks_out: list[StudentProfileBlockOut] = []
        for block in raw_blocks:
            if block.get("selection_rule") == "container" or int(block.get("earned_credits", 0)) <= 0:
                continue
            blocks_out.append(
                StudentProfileBlockOut(
                    block_code=str(block["block_code"]),
                    required_credits=int(block["required_credits"]),
                    earned_credits=int(block["earned_credits"]),
                    counts_toward_total=bool(block["counts_toward_total"]),
                )
            )
        return blocks_out

    # Fallback khi student không có khóa 'blocks': tính theo repo.blocks và passed_courses
    blocks_df = repo.blocks(curriculum_code)
    passed_codes = set(student.get("passed_courses", []))
    passed_courses_df = courses_df[courses_df["course_code"].isin(passed_codes)]
    credits_by_block = passed_courses_df.groupby("block_code")["credits"].sum().to_dict()

    blocks_out = []
    for _, b in blocks_df.iterrows():
        if b.get("selection_rule") == "container":
            continue
        b_code = str(b["block_code"])
        earned = int(credits_by_block.get(b_code, 0))
        if earned <= 0:
            continue
        blocks_out.append(
            StudentProfileBlockOut(
                block_code=b_code,
                required_credits=int(b["required_credits"]),
                earned_credits=earned,
                counts_toward_total=bool(b["counts_toward_total"]),
            )
        )
    return blocks_out


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
        blocks=_extract_blocks(student, repo, curriculum_code, courses_df),
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
    """Ghép trọng số bằng `merge_weights()` và gắn khóa lỗi `weights.<mã>` đúng mục 5."""
    if weights is None:
        return None
    try:
        return merge_weights(weights)
    except ValueError as exc:
        fields: dict[str, str] = {}
        for key, value in weights.items():
            if key not in DEFAULT_WEIGHTS:
                fields[f"weights.{key}"] = f"Trọng số '{key}' không có trong hợp đồng."
            elif (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0
            ):
                fields[f"weights.{key}"] = f"Trọng số '{key}' phải là số lớn hơn hoặc bằng 0."
        if not fields:
            fields["weights"] = str(exc)
        raise ApiError(
            code="validation_error",
            message="Dữ liệu gợi ý không hợp lệ.",
            status=422,
            details={"fields": fields},
        ) from exc


def _recommender_supports_credit_window() -> bool:
    """True khi `src.recommender.recommend` đã nhận `min_credits`, `max_credits`, `include` (RANK-3)."""
    params = inspect.signature(src.recommender.recommend).parameters
    return {"min_credits", "max_credits", "include"}.issubset(params)


def _validate_stub_window(
    curriculum: pd.Series,
    courses_df: pd.DataFrame,
    max_credits: int,
    skip: list[str],
    include: list[str],
) -> None:
    """Kiểm tra đầu vào theo khung cho mục 6.11 khi chạy Stub Fallback (chưa có RANK-3)."""
    cap = int(curriculum["max_credits_per_term"])
    if max_credits > cap:
        raise ValueError(
            f"max_credits: không được vượt {cap} tín chỉ, mức tối đa một học kỳ của khung, nhận được {max_credits}."
        )
    valid_codes = set(courses_df["course_code"].astype(str))
    used: set[str] = set()
    for idx, code in enumerate(skip):
        if code not in valid_codes:
            raise ValueError(f"skip[{idx}]: '{code}' không thuộc khung chương trình đào tạo.")
        if code in used:
            raise ValueError(f"skip[{idx}]: '{code}' đã xuất hiện ở phía trên trong skip hoặc include.")
        used.add(code)
    for idx, code in enumerate(include):
        if code not in valid_codes:
            raise ValueError(f"include[{idx}]: '{code}' không thuộc khung chương trình đào tạo.")
        if code in used:
            raise ValueError(f"include[{idx}]: '{code}' đã xuất hiện ở phía trên trong skip hoặc include.")
        used.add(code)


def _run_recommendation_pipeline(
    repo: Repository,
    uni: str,
    curriculum_code: str,
    curriculum: pd.Series,
    courses_df: pd.DataFrame,
    body: TranscriptRecommendationIn,
) -> TranscriptRecommendationsOut:
    """Chạy luồng Live (`RULES-4`/`DATA-4`/`RANK-3`/`EXPLAIN-2`) hoặc Stub Fallback (§6.11)."""
    merged_weights = _validate_and_merge_weights(body.weights)
    max_credits = body.max_credits if body.max_credits is not None else max(20, body.min_credits)
    student = _build_transcript_student(repo, uni, curriculum_code, curriculum, courses_df, body)

    if student is None or not _recommender_supports_credit_window():
        try:
            if student is None:
                _validate_stub_transcript(curriculum, courses_df, body)
            _validate_stub_window(curriculum, courses_df, max_credits, body.skip, body.include)
        except ValueError as exc:
            api_err = _transcript_value_error(exc)
            if api_err is None:
                raise
            raise api_err from exc
        stub = _CONTRACT_RECOMMENDATIONS_STUB
        return TranscriptRecommendationsOut(
            university_code=uni,
            curriculum_code=curriculum_code,
            algorithm_version=src.recommender.ALGORITHM_VERSION,
            what_if=bool(body.skip or body.include),
            weights=merged_weights if merged_weights is not None else dict(DEFAULT_WEIGHTS),
            target_semester=body.semesters_completed + 1,
            credit_window=CreditWindowOut(
                min_credits=body.min_credits,
                max_credits=max_credits,
                total_credits=stub["credit_window_total"],
                text=stub["credit_window_text"],
            ),
            candidate_count=stub["candidate_count"],
            items=stub["items"],
            not_selected=stub["not_selected"],
            not_eligible=stub["not_eligible"],
            warnings=stub["warnings"],
        )

    try:
        rec: dict[str, Any] = src.recommender.recommend(
            repo,
            student,
            weights=merged_weights,
            skip=list(body.skip) or None,
            include=list(body.include) or None,
            min_credits=body.min_credits,
            max_credits=max_credits,
        )
    except ValueError as exc:
        api_err = _transcript_value_error(exc)
        if api_err is None:
            raise
        raise api_err from exc

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


def _plan_check_supports_credit_window() -> bool:
    """True khi `src.rules.plan.check_plan` đã nhận `min_credits`, `max_credits` (RULES-6)."""
    params = inspect.signature(src.rules.plan.check_plan).parameters
    return {"min_credits", "max_credits"}.issubset(params)


def _plan_total_credits(courses_df: pd.DataFrame, blocks_df: pd.DataFrame, course_codes: list[str]) -> int:
    """Tính tổng tín chỉ kế hoạch: cộng mỗi mã một lần và chỉ cộng khối `counts_toward_total = true`."""
    seen: set[str] = set()
    unique_codes: list[str] = []
    for code in course_codes:
        if code not in seen:
            seen.add(code)
            unique_codes.append(code)

    total = 0
    courses_map = courses_df.set_index("course_code").to_dict("index")
    for code in unique_codes:
        if code in courses_map:
            c_info = courses_map[code]
            b_code = str(c_info["block_code"])
            counts_toward_total = True
            if b_code in blocks_df.index:
                counts_toward_total = bool(blocks_df.loc[b_code]["counts_toward_total"])
            if counts_toward_total:
                total += int(c_info["credits"])
    return total


def _run_plan_check_pipeline(
    repo: Repository,
    uni: str,
    curriculum_code: str,
    curriculum: pd.Series,
    courses_df: pd.DataFrame,
    body: TranscriptPlanCheckIn,
) -> TranscriptPlanCheckOut:
    """Chạy luồng Live (`RULES-4`/`DATA-4`/`RULES-6`) hoặc Stub Fallback khi tầng dưới chưa merge."""
    max_credits = body.max_credits if body.max_credits is not None else max(20, body.min_credits)
    cap = int(curriculum["max_credits_per_term"])
    blocks_df = repo.blocks(curriculum_code).set_index("block_code")
    total_credits = _plan_total_credits(courses_df, blocks_df, body.course_codes)
    student = _build_transcript_student(repo, uni, curriculum_code, curriculum, courses_df, body)

    if student is None or not _plan_check_supports_credit_window():
        try:
            if student is None:
                _validate_stub_transcript(curriculum, courses_df, body)
            if max_credits > cap:
                raise ValueError(
                    f"max_credits: không được vượt {cap} tín chỉ, mức tối đa một học kỳ của khung, nhận được {max_credits}."
                )
        except ValueError as exc:
            api_err = _transcript_value_error(exc)
            if api_err is None:
                raise
            raise api_err from exc
        return TranscriptPlanCheckOut(
            university_code=uni,
            curriculum_code=curriculum_code,
            target_semester=body.semesters_completed + 1,
            min_credits=body.min_credits,
            max_credits=max_credits,
            total_credits=total_credits,
            max_credits_per_term=cap,
            valid=True,
            violations=[],
            warnings=[],
        )

    try:
        violations_raw = src.rules.plan.check_plan(
            repo,
            student,
            body.course_codes,
            min_credits=body.min_credits,
            max_credits=max_credits,
        )
    except ValueError as exc:
        api_err = _transcript_value_error(exc)
        if api_err is None:
            raise
        raise api_err from exc

    courses_by_code: dict[str, dict[str, Any]] = {
        str(r["course_code"]): {**r.to_dict(), "course_code": str(r["course_code"])}
        for _, r in courses_df.iterrows()
    }
    names = {code: str(c["course_name"]) for code, c in courses_by_code.items()}

    violations_list: list[PlanViolationOut] = []
    for v in violations_raw:
        c_obj = courses_by_code.get(v.get("course_code"))
        text_val = v["text"] if v.get("text") is not None else explain.violation_text(v, c_obj, names)
        violations_list.append(
            PlanViolationOut(
                code=str(v["code"]),
                course_code=v.get("course_code"),
                text=text_val,
                data=dict(v.get("data", {})),
            )
        )

    return TranscriptPlanCheckOut(
        university_code=uni,
        curriculum_code=curriculum_code,
        target_semester=int(student.get("target_semester", body.semesters_completed + 1)),
        min_credits=body.min_credits,
        max_credits=max_credits,
        total_credits=total_credits,
        max_credits_per_term=cap,
        valid=len(violations_list) == 0,
        violations=violations_list,
        warnings=_format_warnings(student.get("warnings"), names),
    )


@router.post(
    "/universities/{uni}/curricula/{curriculum_code}/plan-check",
    response_model=TranscriptPlanCheckOut,
    summary="Kiểm tra kế hoạch đăng ký học kỳ từ bảng điểm tự nhập",
    description=(
        "Kiểm tra danh sách học phần sinh viên dự định đăng ký dựa trên bảng điểm tự nhập và khoảng tín chỉ "
        "[min_credits, max_credits], không cần mã sinh viên và không lưu vào cơ sở dữ liệu (mục 6.7)."
    ),
    responses={**ERROR_RESPONSES},
)
def post_curriculum_plan_check(
    uni: str,
    curriculum_code: str,
    body: TranscriptPlanCheckIn,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> TranscriptPlanCheckOut:
    """POST /v1/universities/{uni}/curricula/{curriculum_code}/plan-check (mục 6.7).

    Lưu ý: Bỏ trùng (dedupe) chỉ áp dụng cho `total_credits`; danh sách `body.course_codes` truyền xuống
    `check_plan()` giữ nguyên để tầng luật phát hiện `duplicate_course`.
    """
    validate_university(repo, uni)
    validate_curriculum(repo, uni, curriculum_code)

    curriculum = repo.curriculum(curriculum_code)
    courses_df = repo.curriculum_courses(curriculum_code)
    return _run_plan_check_pipeline(repo, uni, curriculum_code, curriculum, courses_df, body)
