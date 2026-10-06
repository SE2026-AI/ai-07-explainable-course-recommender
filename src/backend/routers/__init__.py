"""HTTP routers grouped by resource. Routers translate DTOs; all logic lives in application/domain."""

from __future__ import annotations

import os

from fastapi import Request

from ..data import CatalogRepository
from ..domain.catalog import CatalogSnapshot, CatalogUnavailable

FAULT_HEADER = "x-ai07-fault"
CATALOG_UNAVAILABLE = "catalog_unavailable"


def faults_of(request: Request) -> frozenset[str]:
    """Fault injection for reliability tests/demo; only honored when AI07_ALLOW_FAULTS=1."""
    if os.environ.get("AI07_ALLOW_FAULTS") != "1" and not getattr(request.app.state, "allow_faults", False):
        return frozenset()
    raw = request.headers.get(FAULT_HEADER, "")
    return frozenset(f.strip() for f in raw.split(",") if f.strip())


def catalog_for(request: Request, version: str | None) -> CatalogSnapshot:
    if CATALOG_UNAVAILABLE in faults_of(request):
        raise CatalogUnavailable(version or "")
    repo: CatalogRepository = request.app.state.catalogs
    return repo.get(version)
