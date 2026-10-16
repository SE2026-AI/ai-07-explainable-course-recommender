"""Router catalog: lịch học kỳ, khung CTĐT, học phần và sơ đồ tiên quyết của trường."""
from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.deps import get_repo
from src.api.schemas.catalog import (
    CurriculumCoursesOut,
    CurriculumDetailOut,
    CurriculumSummaryOut,
    TermOut,
)
from src.api.schemas.common import ERROR_RESPONSES
from src.api.serialization import drop_inapplicable_nulls, to_jsonable
from src.api.services.students import validate_curriculum, validate_university
from src.data.repository import Repository

router = APIRouter(tags=["Danh mục & Chương trình đào tạo"])


@router.get(
    "/universities/{uni}/terms",
    response_model=list[TermOut],
    summary="Lịch học kỳ của trường",
    description="Trả về lịch học kỳ của trường, sắp xếp theo mã học kỳ tăng dần.",
    responses={**ERROR_RESPONSES},
)
async def get_terms(uni: str, repo: Repository = Depends(get_repo)) -> JSONResponse:  # noqa: B008
    """GET /v1/universities/{uni}/terms"""
    validate_university(repo, uni)
    terms_df = repo.terms(uni)
    # Sắp xếp theo code tăng dần (mục 3.3)
    terms_df = terms_df.sort_values(by="term_code")

    data = []
    for _, r in terms_df.iterrows():
        item = {
            "term_code": str(r["term_code"]),
            "term_no": int(r["term_no"]),
            "name": str(r["name"]),
            "academic_year_code": str(r["academic_year_code"]),
            "start_year": int(r["start_year"]),
            "start_date": str(r["start_date"]) if not pd.isna(r.get("start_date")) else None,
            "end_date": str(r["end_date"]) if not pd.isna(r.get("end_date")) else None,
        }
        data.append(to_jsonable(item))
    return JSONResponse(content=drop_inapplicable_nulls(data))


@router.get(
    "/universities/{uni}/curricula",
    response_model=list[CurriculumSummaryOut],
    summary="Danh sách khung CTĐT của trường",
    description="Trả về toàn bộ chương trình đào tạo thuộc trường.",
    responses={**ERROR_RESPONSES},
)
async def get_curricula(uni: str, repo: Repository = Depends(get_repo)) -> JSONResponse:  # noqa: B008
    """GET /v1/universities/{uni}/curricula"""
    validate_university(repo, uni)
    curricula_df = repo.curricula()
    matched = curricula_df[curricula_df["university_code"] == uni].sort_values(by="curriculum_code")

    data = []
    for _, r in matched.iterrows():
        item = {
            "curriculum_code": str(r["curriculum_code"]),
            "university_code": str(r["university_code"]),
            "major_code": str(r["major_code"]),
            "major_name": str(r["major_name"]),
            "name": str(r["name"]),
            "program_type": "standard",
            "effective_from_cohort": int(r["effective_from_cohort"]),
            "effective_to_cohort": int(r["effective_to_cohort"]) if not pd.isna(r.get("effective_to_cohort")) else None,
            "total_credits": int(r["total_credits"]),
            "standard_semesters": int(r["standard_semesters"]),
            "max_credits_per_term": int(r["max_credits_per_term"]),
            "pass_score": float(r["pass_score"]),
            "max_score": float(r["max_score"]),
            "status": str(r["status"]),
        }
        data.append(to_jsonable(item))
    return JSONResponse(content=drop_inapplicable_nulls(data))


@router.get(
    "/universities/{uni}/curricula/{curriculum_code}",
    response_model=CurriculumDetailOut,
    summary="Thông tin khung CTĐT và cây khối kiến thức",
    description="Trả về thông tin chi tiết của một khung CTĐT kèm danh sách khối phẳng (mục 6.2).",
    responses={**ERROR_RESPONSES},
)
async def get_curriculum_detail(
    uni: str,
    curriculum_code: str,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> JSONResponse:
    """GET /v1/universities/{uni}/curricula/{curriculum_code} (mục 6.2)"""
    cur_info = validate_curriculum(repo, uni, curriculum_code)
    blocks_df = repo.blocks(curriculum_code)  # Đã sắp theo sort_order tăng dần (mục 3.3)

    blocks_data = []
    for _, b in blocks_df.iterrows():
        item_block = {
            "block_code": str(b["block_code"]),
            "block_name": str(b["block_name"]),
            "parent_block_code": str(b["parent_block_code"]) if not pd.isna(b.get("parent_block_code")) else None,
            "selection_rule": str(b["selection_rule"]),
            "required_credits": int(b["required_credits"]),
            "counts_toward_total": bool(b["counts_toward_total"]),
            "note": str(b["note"]) if not pd.isna(b.get("note")) else None,
        }
        blocks_data.append(to_jsonable(item_block))

    data = {
        "curriculum_code": str(cur_info["curriculum_code"]),
        "university_code": str(cur_info["university_code"]),
        "major_code": str(cur_info["major_code"]),
        "major_name": str(cur_info["major_name"]),
        "name": str(cur_info["name"]),
        "program_type": "standard",
        "effective_from_cohort": int(cur_info["effective_from_cohort"]),
        "effective_to_cohort": int(cur_info["effective_to_cohort"]) if not pd.isna(cur_info.get("effective_to_cohort")) else None,
        "total_credits": int(cur_info["total_credits"]),
        "standard_semesters": int(cur_info["standard_semesters"]),
        "max_credits_per_term": int(cur_info["max_credits_per_term"]),
        "pass_score": float(cur_info["pass_score"]),
        "max_score": float(cur_info["max_score"]),
        "status": str(cur_info["status"]),
        "blocks": blocks_data,
    }
    return JSONResponse(content=drop_inapplicable_nulls(to_jsonable(data)))


@router.get(
    "/universities/{uni}/curricula/{curriculum_code}/courses",
    response_model=CurriculumCoursesOut,
    summary="Học phần của khung CTĐT",
    description="Trả về toàn bộ học phần trong khung, sắp xếp theo sort_no tăng dần (mục 6.3).",
    responses={**ERROR_RESPONSES},
)
async def get_curriculum_courses(
    uni: str,
    curriculum_code: str,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> JSONResponse:
    """GET /v1/universities/{uni}/curricula/{curriculum_code}/courses (mục 6.3)"""
    validate_curriculum(repo, uni, curriculum_code)
    courses_df = repo.curriculum_courses(curriculum_code)  # Đã sắp theo sort_no

    course_items: list[dict[str, Any]] = []
    for _, r in courses_df.iterrows():
        item = {
            "course_code": str(r["course_code"]),
            "course_name": str(r["course_name"]),
            "course_name_en": str(r["course_name_en"]) if not pd.isna(r.get("course_name_en")) else None,
            "credits": int(r["credits"]),
            "teaching_language": str(r["teaching_language"]) if not pd.isna(r.get("teaching_language")) else None,
            "block_code": str(r["block_code"]),
            "block_name": str(r["block_name"]),
            "is_required": bool(r["is_required"]),
            "recommended_semester": int(r["recommended_semester"]) if not pd.isna(r.get("recommended_semester")) else None,
            "prerequisite_groups": r.get("prerequisite_groups", []),
            "primary_topic": str(r["primary_topic"]) if not pd.isna(r.get("primary_topic")) else None,
            "topics": r.get("topics", []),
            "skills": r.get("skills", []),
        }
        course_items.append(to_jsonable(item))

    return JSONResponse(content=drop_inapplicable_nulls({
        "curriculum_code": curriculum_code,
        "count": len(course_items),
        "courses": course_items,
    }))


