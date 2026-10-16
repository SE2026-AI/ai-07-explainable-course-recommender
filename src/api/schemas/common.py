"""Schema dùng chung cho lỗi và phản hồi HTTP chuẩn."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    """Nội dung trường 'error' trong response lỗi theo hợp đồng mục 5."""
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Dạng lỗi duy nhất của API."""
    error: ErrorBody


ERROR_RESPONSES: dict[int | str, Any] = {
    404: {"model": ErrorResponse, "description": "Tài nguyên không tìm thấy"},
    409: {"model": ErrorResponse, "description": "Xung đột nghiệp vụ (no_primary_program)"},
    422: {"model": ErrorResponse, "description": "Dữ liệu không hợp lệ hoặc chứa khóa lạ"},
    500: {"model": ErrorResponse, "description": "Lỗi nội bộ hệ thống"},
}
