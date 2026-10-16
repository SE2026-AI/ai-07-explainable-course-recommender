"""Giữ tương thích: build/deploy/Dockerfile vẫn chạy `uvicorn src.api.main:app`.

Mã thật nằm ở src/api/app.py.
"""
from src.api.app import app, create_app

__all__ = ["app", "create_app"]

