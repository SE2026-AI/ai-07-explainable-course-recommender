"""Khởi tạo ứng dụng FastAPI cho AI-07 Explainable Course Recommender.

Chạy: uvicorn src.api.app:app --reload

Cấu trúc:
- create_app(): tạo và cấu hình FastAPI app (router, exception handler)
- app: instance dùng cho uvicorn và export_openapi
"""
from __future__ import annotations

from fastapi import FastAPI

from src.api.errors import register_handlers
from src.api.routers import catalog, system
from src.api.version import API_VERSION, CONTRACT_VERSION


def create_app() -> FastAPI:
    """Tạo và cấu hình FastAPI app theo hợp đồng v1.

    Tách ra hàm riêng để:
    1. Test có thể gọi create_app() và ghi đè dependency.
    2. export_openapi.py có thể import mà không kết nối DB.
    """
    app = FastAPI(
        title="AI-07 Explainable Course Recommender API",
        description=(
            "API gợi ý học phần có giải thích (Explainable Course Recommendation) cho dự án AI-07. "
            f"API version: {API_VERSION}. Contract version: {CONTRACT_VERSION}."
        ),
        version=CONTRACT_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Đăng ký exception handler cho tất cả loại lỗi (chuẩn mục 5, không có request_id)
    register_handlers(app)

    # Đăng ký router với tiền tố /v1
    prefix = f"/{API_VERSION}"
    app.include_router(system.router, prefix=prefix)
    app.include_router(catalog.router, prefix=prefix)

    return app


# Instance dùng cho uvicorn và tools/export_openapi.py
app = create_app()
