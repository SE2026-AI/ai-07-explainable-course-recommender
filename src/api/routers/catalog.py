"""Router catalog: lịch học kỳ, khung CTĐT, học phần và sơ đồ tiên quyết của trường."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends

from src.api.deps import get_repo
from src.api.errors import ApiError
from src.api.schemas.catalog import (
    CourseItemOut,
    CurriculumBlockOut,
    CurriculumCoursesOut,
    CurriculumDetailOut,
    CurriculumSummaryOut,
    PrerequisiteGraphEdge,
    PrerequisiteGraphNode,
    PrerequisiteGraphOut,
    TermOut,
)
from src.api.schemas.common import ERROR_RESPONSES
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
def get_terms(uni: str, repo: Repository = Depends(get_repo)) -> list[TermOut]:  # noqa: B008
    """GET /v1/universities/{uni}/terms"""
    validate_university(repo, uni)
    terms_df = repo.terms(uni)
    terms_df = terms_df.sort_values(by="term_code")

    data: list[TermOut] = []
    for _, r in terms_df.iterrows():
        data.append(
            TermOut(
                term_code=str(r["term_code"]),
                term_no=int(r["term_no"]),
                name=str(r["name"]),
                academic_year_code=str(r["academic_year_code"]),
                start_year=int(r["start_year"]),
                start_date=str(r["start_date"]) if not pd.isna(r.get("start_date")) else None,
                end_date=str(r["end_date"]) if not pd.isna(r.get("end_date")) else None,
            )
        )
    return data


@router.get(
    "/universities/{uni}/curricula",
    response_model=list[CurriculumSummaryOut],
    summary="Danh sách khung CTĐT của trường",
    description="Trả về toàn bộ chương trình đào tạo thuộc trường.",
    responses={**ERROR_RESPONSES},
)
def get_curricula(uni: str, repo: Repository = Depends(get_repo)) -> list[CurriculumSummaryOut]:  # noqa: B008
    """GET /v1/universities/{uni}/curricula"""
    validate_university(repo, uni)
    curricula_df = repo.curricula()
    matched = curricula_df[curricula_df["university_code"] == uni].sort_values(by="curriculum_code")

    data: list[CurriculumSummaryOut] = []
    for _, r in matched.iterrows():
        data.append(
            CurriculumSummaryOut(
                curriculum_code=str(r["curriculum_code"]),
                university_code=str(r["university_code"]),
                major_code=str(r["major_code"]),
                major_name=str(r["major_name"]),
                name=str(r["name"]),
                program_type="standard",
                effective_from_cohort=int(r["effective_from_cohort"]),
                effective_to_cohort=int(r["effective_to_cohort"]) if not pd.isna(r.get("effective_to_cohort")) else None,
                total_credits=int(r["total_credits"]),
                standard_semesters=int(r["standard_semesters"]),
                max_credits_per_term=int(r["max_credits_per_term"]),
                pass_score=float(r["pass_score"]),
                max_score=float(r["max_score"]),
                status=str(r["status"]),
            )
        )
    return data


@router.get(
    "/universities/{uni}/curricula/{curriculum_code}",
    response_model=CurriculumDetailOut,
    summary="Thông tin khung CTĐT và cây khối kiến thức",
    description="Trả về thông tin chi tiết của một khung CTĐT kèm danh sách khối phẳng (mục 6.2).",
    responses={**ERROR_RESPONSES},
)
def get_curriculum_detail(
    uni: str,
    curriculum_code: str,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> CurriculumDetailOut:
    """GET /v1/universities/{uni}/curricula/{curriculum_code} (mục 6.2)"""
    cur_info = validate_curriculum(repo, uni, curriculum_code)
    blocks_df = repo.blocks(curriculum_code)

    blocks_data: list[CurriculumBlockOut] = []
    for _, b in blocks_df.iterrows():
        blocks_data.append(
            CurriculumBlockOut(
                block_code=str(b["block_code"]),
                block_name=str(b["block_name"]),
                parent_block_code=str(b["parent_block_code"]) if not pd.isna(b.get("parent_block_code")) else None,
                selection_rule=str(b["selection_rule"]),  # type: ignore[arg-type]
                required_credits=int(b["required_credits"]),
                counts_toward_total=bool(b["counts_toward_total"]),
                note=str(b["note"]) if not pd.isna(b.get("note")) else None,
            )
        )

    return CurriculumDetailOut(
        curriculum_code=str(cur_info["curriculum_code"]),
        university_code=str(cur_info["university_code"]),
        major_code=str(cur_info["major_code"]),
        major_name=str(cur_info["major_name"]),
        name=str(cur_info["name"]),
        program_type="standard",
        effective_from_cohort=int(cur_info["effective_from_cohort"]),
        effective_to_cohort=int(cur_info["effective_to_cohort"]) if not pd.isna(cur_info.get("effective_to_cohort")) else None,
        total_credits=int(cur_info["total_credits"]),
        standard_semesters=int(cur_info["standard_semesters"]),
        max_credits_per_term=int(cur_info["max_credits_per_term"]),
        pass_score=float(cur_info["pass_score"]),
        max_score=float(cur_info["max_score"]),
        status=str(cur_info["status"]),
        blocks=blocks_data,
    )


@router.get(
    "/universities/{uni}/curricula/{curriculum_code}/courses",
    response_model=CurriculumCoursesOut,
    summary="Học phần của khung CTĐT",
    description="Trả về toàn bộ học phần trong khung, sắp xếp theo sort_no tăng dần (mục 6.3).",
    responses={**ERROR_RESPONSES},
)
def get_curriculum_courses(
    uni: str,
    curriculum_code: str,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> CurriculumCoursesOut:
    """GET /v1/universities/{uni}/curricula/{curriculum_code}/courses (mục 6.3)"""
    validate_curriculum(repo, uni, curriculum_code)
    courses_df = repo.curriculum_courses(curriculum_code)

    course_items: list[CourseItemOut] = []
    for _, r in courses_df.iterrows():
        course_items.append(
            CourseItemOut(
                course_code=str(r["course_code"]),
                course_name=str(r["course_name"]),
                course_name_en=str(r["course_name_en"]) if not pd.isna(r.get("course_name_en")) else None,
                credits=int(r["credits"]),
                teaching_language=str(r["teaching_language"]) if not pd.isna(r.get("teaching_language")) else None,
                block_code=str(r["block_code"]),
                block_name=str(r["block_name"]),
                is_required=bool(r["is_required"]),
                recommended_semester=int(r["recommended_semester"]) if not pd.isna(r.get("recommended_semester")) else None,
                prerequisite_groups=r.get("prerequisite_groups", []),
                primary_topic=str(r["primary_topic"]) if not pd.isna(r.get("primary_topic")) else None,
                topics=r.get("topics", []),
                skills=r.get("skills", []),
            )
        )

    return CurriculumCoursesOut(
        curriculum_code=curriculum_code,
        count=len(course_items),
        courses=course_items,
    )


@router.get(
    "/universities/{uni}/curricula/{curriculum_code}/prerequisite-graph",
    response_model=PrerequisiteGraphOut,
    summary="Sơ đồ tiên quyết của khung CTĐT",
    description="Sơ đồ môn nào mở khóa môn nào của một khung CTĐT (mục 6.9).",
    responses={**ERROR_RESPONSES},
)
def get_prerequisite_graph(
    uni: str,
    curriculum_code: str,
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> PrerequisiteGraphOut:
    """GET /v1/universities/{uni}/curricula/{curriculum_code}/prerequisite-graph (mục 6.9)"""
    validate_university(repo, uni)
    validate_curriculum(repo, uni, curriculum_code)

    # TODO(DATA-2): Repository.prerequisite_graph(curriculum_code) -> (nodes_df, edges_df) chưa merge.
    # API không tự dựng đồ thị từ nguồn khác: `group_no` phải là giá trị gốc của bảng prerequisites
    # (§6.9), nên khi chưa có hàm này thì báo lỗi rõ ràng thay vì trả dữ liệu có thể lệch.
    if not hasattr(repo, "prerequisite_graph"):
        raise ApiError(
            code="internal_error",
            message="Lỗi máy chủ nội bộ.",
            status=500,
            details={},
        )
    nodes_df, edges_df = repo.prerequisite_graph(curriculum_code)

    if "sort_no" in nodes_df.columns:
        nodes_df = nodes_df.sort_values(by="sort_no")

    nodes_list: list[PrerequisiteGraphNode] = []
    for _, r in nodes_df.iterrows():
        nodes_list.append(
            PrerequisiteGraphNode(
                course_code=str(r["course_code"]),
                course_name=str(r["course_name"]),
                credits=int(r["credits"]),
                block_code=str(r["block_code"]),
                recommended_semester=(
                    int(r["recommended_semester"])
                    if not pd.isna(r.get("recommended_semester"))
                    else None
                ),
            )
        )

    if not edges_df.empty:
        edges_df = edges_df.sort_values(by=["course_code", "group_no", "required_course_code"])

    edges_list: list[PrerequisiteGraphEdge] = []
    for _, r in edges_df.iterrows():
        edges_list.append(
            PrerequisiteGraphEdge(
                course_code=str(r["course_code"]),
                group_no=int(r["group_no"]),
                required_course_code=str(r["required_course_code"]),
            )
        )

    return PrerequisiteGraphOut(
        curriculum_code=curriculum_code,
        nodes=nodes_list,
        edges=edges_list,
    )