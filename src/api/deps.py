"""Dependency injection cho FastAPI.

get_repo() trả về một instance Repository dùng chung trong suốt vòng đời ứng dụng.
Trong test, ghi đè bằng app.dependency_overrides[get_repo] = lambda: repo_fixture.
"""
from functools import lru_cache

from fastapi import Request

from src.data.repository import Repository


@lru_cache(maxsize=1)
def _create_repo() -> Repository:
    """Tạo Repository một lần duy nhất (kết nối DB lấy từ DATABASE_URL)."""
    return Repository()


def get_repo(request: Request) -> Repository:
    """FastAPI dependency – trả Repository. Test ghi đè bằng dependency_overrides."""
    return _create_repo()

