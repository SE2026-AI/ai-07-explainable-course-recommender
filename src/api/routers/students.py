"""Router cho hồ sơ sinh viên và trạng thái học phần theo hợp đồng mục 6.4 và 6.5."""
from __future__ import annotations

import logging
from collections import Counter

import pandas as pd
from fastapi import APIRouter, Depends, Query

from src.api.deps import get_repo
from src.api.errors import ApiError
from src.api.schemas.common import ERROR_RESPONSES
from src.api.schemas.students import (
    CourseStatusItemOut,
    CourseStatusOut,
    CourseStatusSummaryOut,
    StudentProfileBlockOut,
    StudentProfileOut,
)
from src.api.services.students import build_course_status_item, load_student
from src.data.repository import Repository
from src.recommender.scoring import target_semester
from src.rules.status import course_status_details

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sinh viên"])


@router.get(
    "/universities/{uni}/students/{student_code}/profile",
    response_model=StudentProfileOut,
    summary="Tiến độ học tập của sinh viên",
    description="Trả về thông tin tiến độ học tập của sinh viên theo hợp đồng mục 6.4.",
    responses={**ERROR_RESPONSES},
)
def get_student_profile(
    uni: str,
    student_code: str,
    term: str | None = Query(default=None, description="Mã học kỳ (mặc định target_term_code)"),
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> StudentProfileOut:
    """GET /v1/universities/{uni}/students/{student_code}/profile (mục 6.4)

    Thứ tự kiểm tra lỗi:
    1. university_not_found (404) — qua load_student
    2. student_not_found (404)
    3. no_primary_program (409)
    4. term_not_found (404)
    """
    # Sinh viên đọc đúng mốc `term` (repo.student), nên `year_of_study`, tín chỉ, GPA đều theo kỳ đó.
    student, effective_term = load_student(repo, uni, student_code, term)

    term_row = repo.term(uni, effective_term)
    cohort_year = int(student["cohort_year"])
    year_of_study = int(student["year_of_study"])
    # Công thức mục 3.1 chỉ có một bản, ở tầng xếp hạng: API không tự tính lại.
    target_sem = target_semester(year_of_study, term_row["term_no"])

    curriculum = repo.curriculum(str(student["curriculum_code"]))

    blocks_df = repo.block_progress(int(student["student_id"]), effective_term)
    # Lọc khối lá có tín chỉ tích lũy (earned_credits > 0 và không phải khối container)
    leaf_blocks = blocks_df[
        (blocks_df["selection_rule"] != "container") & (blocks_df["earned_credits"] > 0)
    ]

    blocks_data: list[StudentProfileBlockOut] = []
    for _, b in leaf_blocks.iterrows():
        blocks_data.append(
            StudentProfileBlockOut(
                block_code=str(b["block_code"]),
                required_credits=int(b["required_credits"]),
                earned_credits=int(b["earned_credits"]),
                counts_toward_total=bool(b["counts_toward_total"]),
            )
        )

    gpa_val = float(student["gpa"]) if not pd.isna(student["gpa"]) else None
    if gpa_val is not None:
        gpa_val = round(gpa_val, 2)

    interests_list = student["interests"]
    if not isinstance(interests_list, (list, tuple)):
        interests_list = []

    outstanding_list = student["outstanding_courses"]
    if not isinstance(outstanding_list, (list, tuple)):
        outstanding_list = []

    return StudentProfileOut(
        university_code=str(student["university_code"]),
        student_code=str(student["student_code"]),
        full_name=str(student["full_name"]),
        curriculum_code=str(student["curriculum_code"]),
        major_code=str(student["major_code"]),
        major_name=str(student["major_name"]),
        cohort_year=cohort_year,
        year_of_study=year_of_study,
        term=str(effective_term),
        target_semester=target_sem,
        credits_earned=int(student["credits_earned"]),
        credits_outstanding=int(student["credits_outstanding"]),
        total_credits=int(curriculum["total_credits"]),
        gpa=gpa_val,
        max_credits_per_term=int(curriculum["max_credits_per_term"]),
        interests=list(interests_list),
        outstanding_courses=list(outstanding_list),
        blocks=blocks_data,
    )


@router.get(
    "/universities/{uni}/students/{student_code}/course-status",
    response_model=CourseStatusOut,
    summary="Trạng thái mọi học phần của khung CTĐT",
    description="Trả về trạng thái một học phần đối với sinh viên theo hợp đồng mục 6.5.",
    responses={**ERROR_RESPONSES},
)
def get_student_course_status(
    uni: str,
    student_code: str,
    term: str | None = Query(default=None, description="Mã học kỳ (mặc định target_term_code)"),
    repo: Repository = Depends(get_repo),  # noqa: B008
) -> CourseStatusOut:
    """GET /v1/universities/{uni}/students/{student_code}/course-status (mục 6.5)

    Thứ tự kiểm tra lỗi:
    1. university_not_found (404) — qua load_student
    2. student_not_found (404)
    3. no_primary_program (409)
    4. term_not_found (404)
    """
    # Trạng thái tính trên sinh viên đọc đúng mốc `term` (mục 3.1).
    student, effective_term = load_student(repo, uni, student_code, term)

    status_details = course_status_details(repo, student)
    curriculum_code = str(student["curriculum_code"])
    courses_df = repo.curriculum_courses(curriculum_code)
    # Sắp xếp theo course_code tăng dần (mục 3.3)
    courses_df = courses_df.sort_values(by="course_code")
    # Mã → tên học phần của khung, để câu giải thích gọi tên các môn tiên quyết.
    names = dict(zip(courses_df["course_code"].astype(str), courses_df["course_name"].astype(str), strict=True))

    # Xây courses_list TRƯỚC, rồi tính summary TỪ courses_list (không phải status_details.values())
    # vì courses_df là nguồn chân lý: nó chứa đúng các môn thuộc khung, khớp thứ tự trả về.
    courses_list: list[CourseStatusItemOut] = []
    for _, r in courses_df.iterrows():
        c_code = str(r["course_code"])
        if c_code not in status_details:
            logger.error(
                "course_status_details thiếu mã %s của khung %s đối với sinh viên %s",
                c_code,
                curriculum_code,
                student["student_code"],
            )
            raise ApiError(
                code="internal_error",
                message="Lỗi máy chủ nội bộ.",
                status=500,
                details={},
            )
        courses_list.append(build_course_status_item(r, status_details[c_code], names))

    counts = Counter(c.status for c in courses_list)
    summary = CourseStatusSummaryOut(
        passed=counts.get("passed", 0),
        retake=counts.get("retake", 0),
        eligible=counts.get("eligible", 0),
        missing_prerequisite=counts.get("missing_prerequisite", 0),
        block_complete=counts.get("block_complete", 0),
    )

    if sum(summary.model_dump().values()) != len(courses_list):
        logger.error(
            "Tổng số học phần trong summary (%d) không khớp len(courses) (%d) của sinh viên %s",
            sum(summary.model_dump().values()),
            len(courses_list),
            student["student_code"],
        )

    return CourseStatusOut(
        university_code=str(student["university_code"]),
        student_code=str(student["student_code"]),
        curriculum_code=curriculum_code,
        term=str(effective_term),
        summary=summary,
        courses=courses_list,
    )

