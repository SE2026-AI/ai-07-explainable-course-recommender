"""Dependency injection cho FastAPI.

get_repo() trả về một instance Repository dùng chung trong suốt vòng đời ứng dụng.
Trong test, ghi đè bằng app.dependency_overrides[get_repo] = lambda: repo_fixture.
"""
from __future__ import annotations

from functools import lru_cache

from src.data.repository import Repository


@lru_cache(maxsize=1)
def _create_repo() -> Repository:
    """Tạo Repository một lần duy nhất (kết nối DB lấy từ DATABASE_URL)."""
    return Repository()


def get_repo() -> Repository:
    """FastAPI dependency – trả Repository. Test ghi đè bằng dependency_overrides."""
    return _create_repo()


def dispose_repo() -> None:
    """Giải phóng connection pool của engine khi ứng dụng tắt."""
    if _create_repo.cache_info().currsize > 0:
        repo = _create_repo()
        if hasattr(repo, "engine") and repo.engine is not None:
            repo.engine.dispose()
        _create_repo.cache_clear()
