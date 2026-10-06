"""GET /v1/catalog/* — catalog listing, prerequisite graph, goals and topics."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from .. import CONTRACT_VERSION
from ..errors import request_id_of
from . import catalog_for

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _course_dto(course) -> dict:
    return {
        "course_id": course.course_id, "title": course.title, "credits": course.credits,
        "workload_hours_per_week": course.workload_hours_per_week,
        "mandatory_prerequisites": list(course.mandatory_prerequisites),
        "recommended_preparation": list(course.recommended_preparation),
        "available_terms": list(course.available_terms),
        "topics": list(course.topics),
        "goal_relevance": dict(course.goal_relevance),
    }


@router.get("/courses")
def list_courses(request: Request,
                 catalog_version: str | None = Query(default=None, min_length=1),
                 q: str | None = Query(default=None, max_length=100),
                 limit: int = Query(default=50, ge=1, le=100),
                 cursor: str | None = Query(default=None, pattern=r"^\d+$")):
    catalog = catalog_for(request, catalog_version)
    courses = sorted(catalog.courses.values(), key=lambda c: c.course_id)
    if q:
        needle = q.casefold()
        courses = [c for c in courses if needle in c.course_id.casefold() or needle in c.title.casefold()
                   or any(needle in t.casefold() for t in c.topics)]
    start = int(cursor or 0)
    page = courses[start:start + limit]
    next_cursor = str(start + limit) if start + limit < len(courses) else None
    return {"request_id": request_id_of(request), "contract_version": CONTRACT_VERSION,
            "catalog_version": catalog.catalog_version, "items": [_course_dto(c) for c in page], "next_cursor": next_cursor}


@router.get("/graph")
def graph(request: Request, catalog_version: str = Query(min_length=1)):
    catalog = catalog_for(request, catalog_version)
    return {"request_id": request_id_of(request), "catalog_version": catalog.catalog_version,
            "nodes": sorted(catalog.courses),
            "edges": [{"prerequisite_course_id": p, "dependent_course_id": d} for p, d in catalog.edges()]}


@router.get("/meta")
def meta(request: Request, catalog_version: str | None = Query(default=None, min_length=1)):
    """Goals and topics (interest IDs) a client may offer to the user. Additive to contract 0.1.0."""
    catalog = catalog_for(request, catalog_version)
    return {"request_id": request_id_of(request), "contract_version": CONTRACT_VERSION,
            "catalog_version": catalog.catalog_version, "available_catalog_versions": request.app.state.catalogs.versions,
            "goals": [{"goal_id": g, "title": t} for g, t in sorted(catalog.goals.items())],
            "topics": catalog.topics,
            "terms": sorted({t for c in catalog.courses.values() for t in c.available_terms})}
