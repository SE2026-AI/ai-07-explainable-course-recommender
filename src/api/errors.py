"""Định nghĩa lớp lỗi và exception handlers cho FastAPI theo hợp đồng API v1 mục 5.

Định dạng lỗi chuẩn:
{
  "error": {
    "code": "snake_case",
    "message": "...",
    "details": {}
  }
}

Quy định:
- code: snake_case thường.
- message: tiếng Việt dành cho người đọc.
- details: object (dict), không phải list.
- Tuyệt đối KHÔNG có request_id.
- Áp dụng cả cho validation_error (422) và internal_error (500, không lộ thông tin nội bộ).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("api.errors")


class ApiError(Exception):
    """Lỗi nghiệp vụ của API – handler sẽ chuyển thành JSON chuẩn."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details: dict[str, Any] = details if details is not None else {}


def _format_error_response(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details if details is not None else {},
        }
    }


def register_handlers(app: FastAPI) -> None:
    """Đăng ký tất cả exception handlers vào ứng dụng FastAPI."""

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=_format_error_response(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Xử lý lỗi validate của Pydantic/FastAPI -> 422 validation_error."""
        fields_error: dict[str, str] = {}
        for error in exc.errors():
            loc = error.get("loc", ())
            # Bỏ qua phần tử đầu ("body", "query", "path")
            field_parts = [str(p) for p in loc if p not in ("body", "query", "path")]
            field = ".".join(field_parts) if field_parts else "body"
            fields_error[field] = error.get("msg", "Dữ liệu không hợp lệ")

        return JSONResponse(
            status_code=422,
            content=_format_error_response(
                code="validation_error",
                message="Dữ liệu gửi lên không hợp lệ.",
                details={"fields": fields_error},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Bắt 404 route và các lỗi HTTP của Starlette."""
        if exc.status_code == 404:
            code = "route_not_found"
            message = f"Đường dẫn '{request.url.path}' không tồn tại."
            details = {"path": request.url.path}
        elif exc.status_code == 405:
            code = "method_not_allowed"
            message = f"Phương thức HTTP '{request.method}' không được hỗ trợ cho đường dẫn này."
            details = {"method": request.method, "path": request.url.path}
        else:
            code = "http_error"
            message = str(exc.detail) if exc.detail else "Lỗi HTTP không xác định."
            details = {}

        return JSONResponse(
            status_code=exc.status_code,
            content=_format_error_response(code, message, details),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Bắt mọi lỗi không lường trước -> 500 internal_error (KHÔNG lộ thông tin nội bộ)."""
        logger.exception("Lỗi không lường trước: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_format_error_response(
                code="internal_error",
                message="Đã xảy ra lỗi nội bộ. Vui lòng thử lại sau.",
                details={},
            ),
        )
