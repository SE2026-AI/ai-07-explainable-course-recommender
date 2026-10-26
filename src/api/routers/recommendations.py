"""Router cho gợi ý học phần và kiểm tra kế hoạch học kỳ theo hợp đồng mục 6.6 và 6.7."""
from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, Query

import src.recommender
import src.rules.plan
from src import explain
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
    SwapIn,
)
from src.api.services.students import load_student
from src.data.repository import Repository
from src.recommender.scoring import merge_weights

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Gợi ý & Kế hoạch"])

# Thông điệp ValueError của tầng xếp hạng mở đầu bằng đường dẫn tới trường sai, ví dụ
# "assumptions[1].score: ...", "skip[0]: ...", "swap[2].replacement: ..." (whatif.py).
_FIELD_PATH = re.compile(r"^((?:assumptions|skip|swap)(?:\[\d+\])?(?:\.\w+)?): (.+)$", re.DOTALL)


def _choice_error(exc: ValueError, has_choices: dict[str, bool]) -> ApiError | None:
    """422 validation_error cho ValueError do ĐẦU VÀO sai (`assumptions`, `skip`, `swap`); `None` nếu không phải.

    Trọng số đã được merge_weights() kiểm ở API, nên một ValueError khi request không có `assumptions`,
    `skip` hay `swap` là lỗi nội bộ, không được giả làm 422.
    """
    message = str(exc)
    matched = _FIELD_PATH.match(message)
    if matched:
        fields = {matched.group(1): matched.group(2)}
    else:
        given = [name for name, present in has_choices.items() if present]
        if not given:
            return None
        fields = {given[0]: message}
    return ApiError(
        code="validation_error",
        message="Dữ liệu gợi ý không hợp lệ.",
        status=422,
        details={"fields": fields},
    )


def _handle_recommendations(
    repo: Repository,
    uni: str,
    student_code: str,
    term: str | None,
    limit: int,
    weights: dict[str, float] | None,
    assumptions: list[AssumptionIn] | None,
    skip: list[str] | None = None,
    swap: list[SwapIn] | None = None,
) -> RecommendationsOut:
    """Xử lý chung cho cả GET và POST /v1/.../recommendations (mục 6.6).

    Thứ tự kiểm tra lỗi:
    1. limit (422 validation_error) - FastAPI kiểm trước khi vào handler
    2. university_not_found (404), student_not_found (404), no_primary_program (409), term_not_found (404)
       — qua load_student
    3. weights / assumptions / skip / swap validation (422 validation_error)

    Hàm chỉ ghép: tầng xếp hạng trả `what_if`, `weights`, `candidate_count`, `items`, `not_eligible`; API thêm
    đúng các trường nhận dạng (`university_code`, `student_code`, `curriculum_code`, `term`, `algorithm_version`).
    """
    # Sinh viên đọc đúng mốc `term`; recommend() nhận cùng `term_code` (mục 3.1).
    student, effective_term = load_student(repo, uni, student_code, term)

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

    assumption_list = [a.model_dump() for a in assumptions or []]
    skip_list = list(skip or [])
    swap_list = [pair.model_dump() for pair in swap or []]

    try:
        rec: dict[str, Any] = src.recommender.recommend(
            repo,
            student,
            k=limit,
            weights=merged_weights,
            assumptions=assumption_list or None,
            term_code=effective_term,
            skip=skip_list or None,
            swap=swap_list or None,
        )
    except ValueError as exc:
        api_error = _choice_error(
            exc, {"assumptions": bool(assumption_list), "skip": bool(skip_list), "swap": bool(swap_list)}
        )
        if api_error is None:
            raise
        raise api_error from exc

    return RecommendationsOut(
        university_code=str(student["university_code"]),
        student_code=str(student["student_code"]),
        curriculum_code=str(student["curriculum_code"]),
        term=effective_term,
        algorithm_version=src.recommender.ALGORITHM_VERSION,
        **rec,
    )


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
        skip=None,
        swap=None,
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
        skip=body.skip,
        swap=body.swap,
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
    1. university_not_found (404) — qua load_student
    2. student_not_found (404)
    3. no_primary_program (409)
    4. term_not_found (404)

    Lưu ý: Bỏ trùng (dedupe) chỉ áp dụng cho việc tính `total_credits`; danh sách `body.course_codes`
    truyền xuống check_plan() được giữ nguyên bản để tầng luật phát hiện vi phạm duplicate_course.
    """
    # Kế hoạch được kiểm với sinh viên đọc đúng mốc `term`: môn đã đạt tính trước học kỳ đó.
    student, effective_term = load_student(repo, uni, student_code, body.term)

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

    # check_plan (src/rules/plan.py) và violation_text (src/explain) tra cứu lúc gọi để test thay thế được.
    violations_raw = src.rules.plan.check_plan(repo, student, body.course_codes)

    courses_by_code: dict[str, dict[str, Any]] = {
        str(r["course_code"]): {**r.to_dict(), "course_code": str(r["course_code"])}
        for _, r in courses_df.iterrows()
    }
    # Mã → tên học phần của khung, để câu vi phạm gọi tên các môn tiên quyết còn thiếu.
    names = {code: str(c["course_name"]) for code, c in courses_by_code.items()}

    violations_list: list[PlanViolationOut] = []
    for v in violations_raw:
        c_obj = courses_by_code.get(v.get("course_code"))
        item_v: dict[str, Any] = {
            "code": str(v["code"]),
            "course_code": v.get("course_code"),
            "text": explain.violation_text(v, c_obj, names),
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