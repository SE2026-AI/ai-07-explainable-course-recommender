"""Package schemas cho API v1."""
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
    UniversityOut,
)
from src.api.schemas.common import ERROR_RESPONSES, ErrorBody, ErrorResponse
from src.api.schemas.data_issues import DataIssueItemOut, DataIssuesOut
from src.api.schemas.meta import MetaOut
from src.api.schemas.recommendations import (
    AssumptionIn,
    PlanCheckBodyIn,
    PlanCheckOut,
    PlanViolationOut,
    RecommendationBodyIn,
    RecommendationItemOut,
    RecommendationReasonOut,
    RecommendationsOut,
)
from src.api.schemas.students import (
    CourseStatusItemOut,
    CourseStatusOut,
    CourseStatusSummaryOut,
    LastAttemptOut,
    StatusBlockDetailOut,
    StudentProfileBlockOut,
    StudentProfileOut,
)

__all__ = [
    "ERROR_RESPONSES",
    "AssumptionIn",
    "CourseItemOut",
    "CourseStatusItemOut",
    "CourseStatusOut",
    "CourseStatusSummaryOut",
    "CurriculumBlockOut",
    "CurriculumCoursesOut",
    "CurriculumDetailOut",
    "CurriculumSummaryOut",
    "DataIssueItemOut",
    "DataIssuesOut",
    "ErrorBody",
    "ErrorResponse",
    "LastAttemptOut",
    "MetaOut",
    "PlanCheckBodyIn",
    "PlanCheckOut",
    "PlanViolationOut",
    "PrerequisiteGraphEdge",
    "PrerequisiteGraphNode",
    "PrerequisiteGraphOut",
    "RecommendationBodyIn",
    "RecommendationItemOut",
    "RecommendationReasonOut",
    "RecommendationsOut",
    "StatusBlockDetailOut",
    "StudentProfileBlockOut",
    "StudentProfileOut",
    "TermOut",
    "UniversityOut",
]
