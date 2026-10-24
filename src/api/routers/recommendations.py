"""Router cho gợi ý học phần và kiểm tra kế hoạch học kỳ theo hợp đồng mục 6.6 và 6.7."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

import src.recommender
from src import explain, rules
from src.api.deps import get_repo
from src.api.errors import ApiError
from src.api.schemas.common import ERROR_RESPONSES
from src.api.schemas.recommendations import (
    AssumptionIn,
    PlanCheckBodyIn,
    PlanCheckOut,
    PlanViolationOut,
    RecommendationBodyIn,
    RecommendationsOut,
)
from src.api.services.students import (
    validate_student,
    validate_term,
)
from src.data.repository import Repository
from src.recommender.scoring import merge_weights

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Gợi ý & Kế hoạch"])


def _handle_recommendations(
    repo: Repository,
    uni: str,
    student_code: str,
    term: str | None,
    limit: int,
    weights: dict[str, float] | None,
    assumptions: list[AssumptionIn] | None,
) -> RecommendationsOut:
    """Xử lý chung cho cả GET và POST /v1/.../recommendations (mục 6.6).

    Thứ tự kiểm tra lỗi:
    1. limit (422 validation_error) - FastAPI kiểm trước khi vào handler
    2. university_not_found (404) — qua validate_student
    3. student_not_found (404)
    4. no_primary_program (409)
    5. term_not_found (404)
    6. weights / assumptions validation (422 validation_error)
    """
    # `limit` đã được FastAPI kiểm (ge=1, le=20) trước khi vào đây.
    # validate_student gọi validate_university bên trong → không cần gọi riêng
    student = validate_student(repo, uni, student_code)
    effective_term = validate_term(repo, uni, term)

    merged_weights = None
    if weights is not None:
        try:
            merged_weights = merge_weights(weights)
        except ValueError as exc:
            raise ApiError(
                code="validation_error",
                message="Trọng số không hợp lệ.",
                status=422,
                details={"fields": {"weights": str(exc)}},
            ) from exc

    # Kiểm tra nội dung `assumptions` (mã môn thuộc khung, điểm trong thang) thuộc apply_assumptions()
    # của tầng recommender (RANK-2); API chỉ kiểm hình dạng body qua schema (AssumptionIn, extra="forbid").
    assumptions_list = assumptions or []

    # recommend(repo, student, k=5, weights=None, assumptions=None) -> dict (chữ ký công bố, RANK-2).
    # Trọng số đã được merge_weights() kiểm ở trên, nên ValueError từ recommend() chỉ được coi là lỗi
    # đầu vào khi request có assumptions; ngoài ra để lỗi nổi lên thành 500 thay vì giả làm 422.
    try:
        rec_result: Any = src.recommender.recommend(
            repo,
            student,
            k=limit,
            weights=merged_weights,
            assumptions=[a.model_dump() for a in assumptions_list] if assumptions_list else None,
        )
    except ValueError as exc:
        if not assumptions_list:
            raise
        raise ApiError(
            code="validation_error",
            message="Tham số assumptions không hợp lệ.",
            status=422,
            details={"fields": {"assumptions": str(exc)}},
        ) from exc

    if not isinstance(rec_result, dict):
        logger.error(
            "recommend() trả về %s thay vì dict cho sinh viên %s",
            type(rec_result).__name__,
            student_code,
        )
        raise ApiError(
            code="internal_error",
            message="Lỗi máy chủ nội bộ.",
            status=500,
            details={},
        )

    # `what_if` do API quyết định theo hợp đồng (mục 6.6 quy định 6), không phụ thuộc tầng dưới.
    # TODO(RANK-2): recommend() chưa nhận `term`; đến khi có, `term` chỉ được ghi lại, chưa đổi kết quả.
    return RecommendationsOut(**{**rec_result, "term": effective_term, "what_if": bool(assumptions_list)})


@router.get(
    "/universities/{uni}/students/{student_code}/recommendations",
    response_model=RecommendationsOut,
    summary="Gợi ý học phần cho kỳ tới",
    description="Trả về danh sách học phần được gợi ý xếp hạng theo hợp đồng mục 6.6.",
    responses={**ERROR_RESPONSES},
)
def get_recommendations(
    uni: str,
    student_code: str,
    term: str | None = Query(default=None, description="Mã học kỳ (mặc định target_term_code)"),
    limit: int = Query(default=5, ge=1, le=20, description="Số học phần tối đa cần gợi ý (1-20)"),
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> RecommendationsOut:
    """GET /v1/universities/{uni}/students/{student_code}/recommendations (mục 6.6)"""
    return _handle_recommendations(
        repo=repo,
        uni=uni,
        student_code=student_code,
        term=term,
        limit=limit,
        weights=None,
        assumptions=None,
    )


@router.post(
    "/universities/{uni}/students/{student_code}/recommendations",
    response_model=RecommendationsOut,
    summary="Gợi ý học phần với trọng số tùy chỉnh và giả định",
    description="Gợi ý học phần có thể kèm trọng số tùy chỉnh và kịch bản what-if (mục 6.6).",
    responses={**ERROR_RESPONSES},
)
def post_recommendations(
    uni: str,
    student_code: str,
    body: RecommendationBodyIn,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> RecommendationsOut:
    """POST /v1/universities/{uni}/students/{student_code}/recommendations (mục 6.6)"""
    return _handle_recommendations(
        repo=repo,
        uni=uni,
        student_code=student_code,
        term=body.term,
        limit=body.limit,
        weights=body.weights,
        assumptions=body.assumptions,
    )


@router.post(
    "/universities/{uni}/students/{student_code}/plan-check",
    response_model=PlanCheckOut,
    summary="Kiểm tra kế hoạch đăng ký học kỳ",
    description="Kiểm tra kế hoạch học tập sinh viên dự định đăng ký theo hợp đồng mục 6.7.",
    responses={**ERROR_RESPONSES},
)
def post_plan_check(
    uni: str,
    student_code: str,
    body: PlanCheckBodyIn,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> PlanCheckOut:
    """POST /v1/universities/{uni}/students/{student_code}/plan-check (mục 6.7)

    Thứ tự kiểm tra lỗi:
    1. university_not_found (404) — qua validate_student
    2. student_not_found (404)
    3. no_primary_program (409)
    4. term_not_found (404)

    Lưu ý: Bỏ trùng (dedupe) chỉ áp dụng cho việc tính `total_credits`; danh sách `body.course_codes`
    truyền xuống check_plan() được giữ nguyên bản để tầng luật phát hiện vi phạm duplicate_course.
    """
    # validate_student gọi validate_university bên trong → không cần gọi riêng
    student = validate_student(repo, uni, student_code)
    effective_term = validate_term(repo, uni, body.term)

    curriculum_code = str(student["curriculum_code"])
    curriculum = repo.curriculum(curriculum_code)
    max_credits = int(curriculum["max_credits_per_term"])

    courses_df = repo.curriculum_courses(curriculum_code)
    blocks_df = repo.blocks(curriculum_code).set_index("block_code")

    # total_credits chỉ cộng MỖI mã học phần một lần (giữ thứ tự, bỏ trùng)
    # và chỉ cộng học phần thuộc khối có counts_toward_total = true (mục 6.7)
    seen_codes: set[str] = set()
    unique_course_codes: list[str] = []
    for code in body.course_codes:
        if code not in seen_codes:
            seen_codes.add(code)
            unique_course_codes.append(code)

    total_credits = 0
    courses_map = courses_df.set_index("course_code").to_dict("index")
    for code in unique_course_codes:
        if code in courses_map:
            c_info = courses_map[code]
            b_code = str(c_info["block_code"])
            counts_toward_total = True
            if b_code in blocks_df.index:
                counts_toward_total = bool(blocks_df.loc[b_code]["counts_toward_total"])
            if counts_toward_total:
                total_credits += int(c_info["credits"])

    # check_plan (RULES-2) và violation_text (EXPLAIN-1) tra cứu lúc gọi để test thay thế được.
    violations_raw = rules.check_plan(repo, student, body.course_codes)

    courses_by_code: dict[str, dict[str, Any]] = {
        str(r["course_code"]): {**r.to_dict(), "course_code": str(r["course_code"])}
        for _, r in courses_df.iterrows()
    }

    violations_list: list[PlanViolationOut] = []
    for v in violations_raw:
        c_obj = courses_by_code.get(v.get("course_code"))
        item_v: dict[str, Any] = {
            "code": str(v["code"]),
            "course_code": v.get("course_code"),
            "text": explain.violation_text(v, c_obj),
            "data": dict(v.get("data", {})),
        }
        violations_list.append(PlanViolationOut(**item_v))

    valid = len(violations_list) == 0

    return PlanCheckOut(
        university_code=str(student["university_code"]),
        student_code=str(student["student_code"]),
        term=str(effective_term),
        total_credits=total_credits,
        max_credits_per_term=max_credits,
        valid=valid,
        violations=violations_list,
    )