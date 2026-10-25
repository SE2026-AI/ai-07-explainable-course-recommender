"""Service tra cứu và kiểm tra ràng buộc sinh viên, trường học, học kỳ."""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import pandas as pd

from src import explain
from src.api.errors import ApiError
from src.api.schemas.students import (
    CourseStatusItemOut,
    LastAttemptOut,
    StatusBlockDetailOut,
)
from src.data.repository import Repository


def validate_university(repo: Repository, university_code: str) -> None:
    """Kiểm tra trường đại học tồn tại. Nếu không -> 404 university_not_found."""
    unis = repo.universities()
    if university_code not in unis["university_code"].values:
        raise ApiError(
            code="university_not_found",
            message=f"Không tìm thấy trường đại học '{university_code}'.",
            status=404,
            details={"university_code": university_code},
        )


def validate_curriculum(repo: Repository, university_code: str, curriculum_code: str) -> pd.Series:
    """Kiểm tra khung CTĐT tồn tại và thuộc trường. Nếu không -> 404 curriculum_not_found."""
    curricula = repo.curricula()
    matched = curricula[
        (curricula["curriculum_code"] == curriculum_code)
        & (curricula["university_code"] == university_code)
    ]
    if matched.empty:
        raise ApiError(
            code="curriculum_not_found",
            message=f"Không tìm thấy chương trình đào tạo '{curriculum_code}' của trường {university_code}.",
            status=404,
            details={"university_code": university_code, "curriculum_code": curriculum_code},
        )
    return matched.iloc[0]


def validate_term(repo: Repository, university_code: str, term: str | None) -> str:
    """Kiểm tra học kỳ có trong lịch của trường. Mặc định là target_term_code. Nếu không -> 404 term_not_found."""
    effective_term = term if term is not None else repo.setting("target_term_code")
    terms_df = repo.terms(university_code)
    matched = terms_df[terms_df["term_code"].astype(str) == str(effective_term)]
    if matched.empty:
        raise ApiError(
            code="term_not_found",
            message=f"Mã học kỳ '{effective_term}' không có trong lịch của trường {university_code}.",
            status=404,
            details={"term": str(effective_term)},
        )
    return str(effective_term)


def load_student(
    repo: Repository, university_code: str, student_code: str, term: str | None = None
) -> tuple[pd.Series, str]:
    """Đọc MỘT sinh viên đúng mốc `term` và trả `(sinh viên, mã học kỳ hiệu lực)`.

    Sinh viên đọc bằng `repo.student(uni, code, term)`: môn đã đạt, điểm, tín chỉ, GPA và `year_of_study`
    đều tính theo đầu học kỳ `term` (mục 3.1), nên mọi endpoint dùng chung một mốc với `recommend(term_code=...)`.

    Thứ tự kiểm tra lỗi (mục 5):
    1. university_not_found (404)
    2. student_not_found (404): trường không có sinh viên này ở bất kỳ CTĐT nào
    3. no_primary_program (409): không có CTĐT vừa chính vừa `active`
    4. term_not_found (404)
    """
    validate_university(repo, university_code)

    programs = repo.student_programs(university_code, student_code)
    if programs.empty:
        raise ApiError(
            code="student_not_found",
            message=f"Không tìm thấy sinh viên {student_code} của trường {university_code}.",
            status=404,
            details={"university_code": university_code, "student_code": student_code},
        )
    primary = programs[programs["is_primary"].astype(bool) & (programs["status"] == "active")]
    if primary.empty:
        raise ApiError(
            code="no_primary_program",
            message=f"Sinh viên {student_code} không có chương trình đào tạo chính đang hoạt động.",
            status=409,
            details={"university_code": university_code, "student_code": student_code},
        )

    effective_term = validate_term(repo, university_code, term)
    student = repo.student(university_code, student_code, effective_term)
    if student is None:
        # student_programs() thấy CTĐT chính đang hoạt động mà student() không thấy: hai đường đọc lệch nhau.
        raise ApiError(
            code="no_primary_program",
            message=f"Sinh viên {student_code} không có chương trình đào tạo chính đang hoạt động.",
            status=409,
            details={"university_code": university_code, "student_code": student_code},
        )
    return student, effective_term


def build_course_status_item(
    course_row: pd.Series, detail: dict[str, Any], names: Mapping[str, str]
) -> CourseStatusItemOut:
    """Xây dựng CourseStatusItemOut từ hàng học phần và chi tiết trạng thái (mục 6.5).

    `names` là bảng mã → tên học phần của khung, để câu giải thích gọi tên các môn tiên quyết."""
    code = str(course_row["course_code"])
    st = detail["status"]

    item_kwargs: dict[str, Any] = {
        "course_code": code,
        "course_name": str(course_row["course_name"]),
        "credits": int(course_row["credits"]),
        "block_code": str(course_row["block_code"]),
        "status": st,
    }

    if st == "missing_prerequisite" and "missing_prerequisites" in detail:
        item_kwargs["missing_prerequisites"] = detail["missing_prerequisites"]
    elif st == "block_complete" and "block" in detail:
        b = detail["block"]
        item_kwargs["block"] = StatusBlockDetailOut(
            block_code=str(b["block_code"]),
            block_name=str(b["block_name"]),
            required_credits=int(b["required_credits"]),
            earned_credits=int(b["earned_credits"]),
        )
    elif st in ("passed", "retake") and "last_attempt" in detail:
        la = detail["last_attempt"]
        score_val = la.get("score")
        item_kwargs["last_attempt"] = LastAttemptOut(
            term_code=str(la["term_code"]),
            attempt_no=int(la["attempt_no"]),
            score=(
                None
                if score_val is None
                or pd.isna(score_val)
                or (isinstance(score_val, (int, float)) and math.isnan(float(score_val)))
                else float(score_val)
            ),
            letter_grade=(
                str(la["letter_grade"])
                if (la.get("letter_grade") is not None and not pd.isna(la.get("letter_grade")))
                else None
            ),
        )

    # status_text do src.explain cung cấp (EXPLAIN-1); tra cứu lúc gọi để test thay thế được.
    course_obj = {**course_row.to_dict(), "course_code": code}
    item_kwargs["text"] = explain.status_text(course_obj, detail, names)

    return CourseStatusItemOut(**item_kwargs)
