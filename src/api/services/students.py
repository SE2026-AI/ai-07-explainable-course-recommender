"""Service tra cứu và kiểm tra ràng buộc trường học, chương trình đào tạo."""
from __future__ import annotations

import pandas as pd

from src.api.errors import ApiError
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
