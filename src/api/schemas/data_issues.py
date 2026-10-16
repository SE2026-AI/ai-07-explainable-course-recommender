"""Schema cho endpoint GET /v1/data-issues (mục 6.8)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DataIssueStatus = Literal["open", "resolved_in_data", "closed"]


class DataIssueItemOut(BaseModel):
    """Thông tin một vấn đề dữ liệu."""
    source_code: str
    source_title: str
    document_number: str
    entity_type: str
    entity_key: str
    issue_type: str
    description: str
    status: DataIssueStatus


class DataIssuesOut(BaseModel):
    """Danh sách các vấn đề dữ liệu."""
    count: int
    issues: list[DataIssueItemOut] = Field(default_factory=list)

