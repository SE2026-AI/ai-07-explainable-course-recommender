"""Package schemas cho API v1."""
from src.api.schemas.catalog import (
    CourseItemOut,
    CurriculumBlockOut,
    CurriculumCoursesOut,
    CurriculumDetailOut,
    CurriculumSummaryOut,
    TermOut,
    UniversityOut,
)
from src.api.schemas.common import ERROR_RESPONSES, ErrorBody, ErrorResponse
from src.api.schemas.data_issues import DataIssueItemOut, DataIssuesOut
from src.api.schemas.meta import MetaOut

__all__ = [
    "ERROR_RESPONSES",
    "CourseItemOut",
    "CurriculumBlockOut",
    "CurriculumCoursesOut",
    "CurriculumDetailOut",
    "CurriculumSummaryOut",
    "DataIssueItemOut",
    "DataIssuesOut",
    "ErrorBody",
    "ErrorResponse",
    "MetaOut",
    "TermOut",
    "UniversityOut",
]
