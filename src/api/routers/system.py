"""Router các endpoint hệ thống: health, meta, universities, data-issues."""
from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.deps import _create_repo, get_repo
from src.api.schemas.catalog import UniversityOut
from src.api.schemas.common import ERROR_RESPONSES, ErrorResponse
from src.api.schemas.data_issues import DataIssueItemOut, DataIssuesOut
from src.api.schemas.meta import MetaOut
from src.api.version import CONTRACT_VERSION
from src.data.repository import Repository
from src.recommender import ALGORITHM, ALGORITHM_VERSION

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Hệ thống"])

# Mở rộng ERROR_RESPONSES thêm 503 cho riêng endpoint /health
_HEALTH_RESPONSES = {
    **ERROR_RESPONSES,
    503: {
        "model": ErrorResponse,
        "description": "Cơ sở dữ liệu không khả dụng",
    },
}


@router.get(
    "/health",
    summary="Kiểm tra dịch vụ còn sống",
    description="Kiểm tra kết nối tới cơ sở dữ liệu PostgreSQL.",
    responses={**_HEALTH_RESPONSES},
)
def get_health() -> JSONResponse:
    """GET /v1/health (mục 5)

    Không dùng Depends(get_repo) vì cần bắt lỗi ngay cả khi tạo Repository thất bại.
    Khi DB down, trả 503 theo đúng envelope §5.
    """
    try:
        repo = _create_repo()
        repo.setting("schema_version")
        return JSONResponse(content={"status": "ok", "database": "up"}, status_code=200)
    except Exception:
        logger.warning("Health check thất bại: database không khả dụng")
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "service_unavailable",
                    "message": "Cơ sở dữ liệu không khả dụng.",
                    "details": {"database": "down"},
                }
            },
        )


@router.get(
    "/meta",
    response_model=MetaOut,
    summary="Thông tin phiên bản và cấu hình",
    description="Trả về phiên bản API, phiên bản lược đồ, thuật toán, học kỳ mặc định và danh sách khung.",
    responses={**ERROR_RESPONSES},
)
def get_meta(repo: Repository = Depends(get_repo)) -> MetaOut:  # noqa: B008
    """GET /v1/meta (mục 6.1)"""
    schema_version = repo.setting("schema_version")
    default_term = repo.setting("target_term_code")
    curricula_df = repo.curricula()
    curriculum_codes = sorted(curricula_df["curriculum_code"].tolist())

    return MetaOut(
        api_version=CONTRACT_VERSION,
        schema_version=schema_version,
        algorithm=ALGORITHM,
        algorithm_version=ALGORITHM_VERSION,
        default_term=default_term,
        curriculum_codes=curriculum_codes,
    )


@router.get(
    "/universities",
    response_model=list[UniversityOut],
    summary="Danh sách trường",
    description="Trả về danh sách trường đại học trong hệ thống.",
    responses={**ERROR_RESPONSES},
)
def get_universities(repo: Repository = Depends(get_repo)) -> list[UniversityOut]:  # noqa: B008
    """GET /v1/universities"""
    unis = repo.universities()
    data: list[UniversityOut] = []
    for _, r in unis.iterrows():
        data.append(
            UniversityOut(
                university_code=str(r["university_code"]),
                name=str(r["name"]),
                name_en=str(r["name_en"]) if not pd.isna(r.get("name_en")) else None,
                short_name=str(r["short_name"]) if not pd.isna(r.get("short_name")) else None,
                is_demo=bool(r["is_demo"]),
            )
        )
    return data


@router.get(
    "/data-issues",
    response_model=DataIssuesOut,
    summary="Các vấn đề dữ liệu",
    description="Các chỗ văn bản gốc mâu thuẫn hoặc thiếu (mục 6.8).",
    responses={**ERROR_RESPONSES},
)
def get_data_issues(repo: Repository = Depends(get_repo)) -> DataIssuesOut:  # noqa: B008
    """GET /v1/data-issues"""
    issues_df = repo.data_issues()
    items: list[DataIssueItemOut] = []
    for _, r in issues_df.iterrows():
        items.append(
            DataIssueItemOut(
                source_code=str(r["source_code"]),
                source_title=str(r["source_title"]),
                document_number=str(r["document_number"]),
                entity_type=str(r["entity_type"]),
                entity_key=str(r["entity_key"]),
                issue_type=str(r["issue_type"]),
                description=str(r["description"]),
                status=str(r["status"]),  # type: ignore[arg-type]
            )
        )

    return DataIssuesOut(count=len(items), issues=items)
