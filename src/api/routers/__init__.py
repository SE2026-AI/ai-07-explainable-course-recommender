"""Package routers cho API v1."""
from src.api.routers import catalog, recommendations, students, system

__all__ = [
    "catalog",
    "recommendations",
    "students",
    "system",
]
