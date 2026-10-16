"""Schema cho endpoint GET /v1/meta."""
from __future__ import annotations

from pydantic import BaseModel


class MetaOut(BaseModel):
    """Thông tin phiên bản và cấu hình hệ thống (mục 6.1)."""
    api_version: str
    schema_version: str
    algorithm: str
    algorithm_version: str
    default_term: str
    curriculum_codes: list[str]

