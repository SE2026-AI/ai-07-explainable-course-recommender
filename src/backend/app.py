"""FastAPI application entrypoint.

Run locally (from repository root):
    uvicorn --app-dir src backend.app:app --reload
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import CONTRACT_VERSION
from . import errors
from .data import CatalogRepository
from .domain.ranking import ALGORITHM_VERSION
from .errors import request_id_of
from .routers import catalog, recommendations


def create_app(repository: CatalogRepository | None = None, *, allow_faults: bool = False) -> FastAPI:
    app = FastAPI(title="AI-07 Explainable Course Recommender", version=CONTRACT_VERSION,
                  docs_url="/v1/docs", openapi_url="/v1/openapi.json")
    app.state.catalogs = repository or CatalogRepository.from_directory()  # invalid snapshot fails startup
    app.state.allow_faults = allow_faults
    origins = os.environ.get("AI07_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in origins if o.strip()],
                       allow_methods=["GET", "POST"], allow_headers=["*"], expose_headers=["X-Request-ID"])

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        rid = request_id_of(request)
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", getattr(request.state, "request_id", rid))
        return response

    errors.install(app)
    app.include_router(catalog.router, prefix="/v1")
    app.include_router(recommendations.router, prefix="/v1")

    @app.get("/v1/health", tags=["ops"])
    def health():
        repo: CatalogRepository = app.state.catalogs
        return {"status": "ok", "contract_version": CONTRACT_VERSION, "algorithm_version": ALGORITHM_VERSION,
                "catalog_versions": repo.versions, "default_catalog_version": repo.default_version}

    return app


app = create_app()
