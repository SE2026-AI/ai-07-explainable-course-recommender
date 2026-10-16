"""Router các endpoint hệ thống: health, meta, universities, data-issues."""
from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.deps import get_repo
from src.api.schemas.catalog import UniversityOut
from src.api.schemas.common import ERROR_RESPONSES
from src.api.schemas.data_issues import DataIssuesOut
from src.api.schemas.meta import MetaOut
from src.api.serialization import drop_inapplicable_nulls, to_jsonable
from src.api.version import CONTRACT_VERSION
from src.data.repository import Repository

try:
    from src.recommender import ALGORITHM, ALGORITHM_VERSION
except ImportError:  # TODO: bỏ khối dự phòng khi module xếp hạng được merge vào main
    ALGORITHM = "rule_based_weighted"
    ALGORITHM_VERSION = "1.0.0"

router = APIRouter(tags=["Hệ thống"])


@router.get(
    "/health",
    summary="Kiểm tra dịch vụ còn sống",
    description="Kiểm tra kết nối tới cơ sở dữ liệu PostgreSQL.",
    responses={**ERROR_RESPONSES},
)
async def get_health(repo: Repository = Depends(get_repo)) -> JSONResponse:  # noqa: B008
    """GET /v1/health"""
    repo.setting("schema_version")
    return JSONResponse(content={"status": "ok", "database": "up"})


@router.get(
    "/meta",
    response_model=MetaOut,
    summary="Thông tin phiên bản và cấu hình",
    description="Trả về phiên bản API, phiên bản lược đồ, thuật toán, học kỳ mặc định và danh sách khung.",
    responses={**ERROR_RESPONSES},
)
async def get_meta(repo: Repository = Depends(get_repo)) -> JSONResponse:  # noqa: B008
    """GET /v1/meta (mục 6.1)"""
    schema_version = repo.setting("schema_version")
    default_term = repo.setting("target_term_code")
    curricula_df = repo.curricula()
    curriculum_codes = sorted(curricula_df["curriculum_code"].tolist())

    data = {
        "api_version": CONTRACT_VERSION,
        "schema_version": schema_version,
        "algorithm": ALGORITHM,
        "algorithm_version": ALGORITHM_VERSION,
        "default_term": default_term,
        "curriculum_codes": curriculum_codes,
    }
    return JSONResponse(content=drop_inapplicable_nulls(data))


@router.get(
    "/universities",
    response_model=list[UniversityOut],
    summary="Danh sách trường",
    description="Trả về danh sách trường đại học trong hệ thống.",
    responses={**ERROR_RESPONSES},
)
async def get_universities(repo: Repository = Depends(get_repo)) -> JSONResponse:  # noqa: B008
    """GET /v1/universities"""
    unis = repo.universities()
    data = []
    for _, r in unis.iterrows():
        item = {
            "university_code": str(r["university_code"]),
            "name": str(r["name"]),
            "name_en": str(r["name_en"]) if not pd.isna(r.get("name_en")) else None,
            "short_name": str(r["short_name"]) if not pd.isna(r.get("short_name")) else None,
            "is_demo": bool(r["is_demo"]),
        }
        data.append(to_jsonable(item))
    return JSONResponse(content=drop_inapplicable_nulls(data))


@router.get(
    "/data-issues",
    response_model=DataIssuesOut,
    summary="Các vấn đề dữ liệu",
    description="Các chỗ văn bản gốc mâu thuẫn hoặc thiếu (mục 6.8).",
    responses={**ERROR_RESPONSES},
)
async def get_data_issues(repo: Repository = Depends(get_repo)) -> JSONResponse:  # noqa: B008
    """GET /v1/data-issues"""
    issues_df = repo.data_issues()
    items: list[dict[str, Any]] = []
    for _, r in issues_df.iterrows():
        items.append({
            "source_code": str(r["source_code"]),
            "source_title": str(r["source_title"]),
            "document_number": str(r["document_number"]),
            "entity_type": str(r["entity_type"]),
            "entity_key": str(r["entity_key"]),
            "issue_type": str(r["issue_type"]),
            "description": str(r["description"]),
            "status": str(r["status"]),
        })

    return JSONResponse(content=drop_inapplicable_nulls({
        "count": len(items),
        "issues": items,
    }))
