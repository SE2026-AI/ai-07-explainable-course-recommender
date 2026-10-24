"""Khởi tạo ứng dụng FastAPI cho AI-07 Explainable Course Recommender.

Chạy: uvicorn src.api.app:app --reload

Cấu trúc:
- create_app(): tạo và cấu hình FastAPI app (router, exception handler, lifespan)
- app: instance dùng cho uvicorn và export_openapi
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.deps import dispose_repo
from src.api.errors import register_handlers
from src.api.routers import catalog, recommendations, students, system
from src.api.serialization import CleanJSONResponse
from src.api.version import API_VERSION, CONTRACT_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Quản lý vòng đời ứng dụng: giải phóng tài nguyên database khi dừng."""
    yield
    dispose_repo()


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
        default_response_class=CleanJSONResponse,
        lifespan=lifespan,
    )

    # Đăng ký exception handler cho tất cả loại lỗi (chuẩn mục 5, không có request_id)
    register_handlers(app)

    # Đăng ký router với tiền tố /v1 (tổng cộng 14 endpoint theo hợp đồng)
    prefix = f"/{API_VERSION}"
    app.include_router(system.router, prefix=prefix)
    app.include_router(catalog.router, prefix=prefix)
    app.include_router(students.router, prefix=prefix)
    app.include_router(recommendations.router, prefix=prefix)

    return app


# Instance dùng cho uvicorn và tools/export_openapi.py
app = create_app()
