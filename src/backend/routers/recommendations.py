"""POST /v1/profiles/validate, /recommendations, /why-not, /simulations."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..application import recommend as uc
from ..domain.profile import check_profile
from ..errors import request_id_of
from ..schemas import BaseRequest, RecommendationRequest, SimulationRequest, WhyNotRequest
from . import catalog_for, faults_of

router = APIRouter(tags=["recommendations"])


def _rid(request: Request, body: BaseRequest) -> str:
    if body.request_id:
        request.state.request_id = body.request_id
    return request_id_of(request)


@router.post("/profiles/validate")
def validate_profile(request: Request, body: BaseRequest):
    catalog = catalog_for(request, body.catalog_version)
    errors, warnings = check_profile(body.profile.to_domain(), catalog)
    return {"request_id": _rid(request, body), "catalog_version": catalog.catalog_version, "valid": not errors,
            "errors": [e.as_dict() for e in errors], "warnings": [w.as_dict() for w in warnings]}


@router.post("/recommendations")
def recommendations(request: Request, body: RecommendationRequest):
    catalog = catalog_for(request, body.catalog_version)
    return uc.recommend(catalog, body.profile.to_domain(), body.weights.as_mapping() if body.weights else None,
                        request_id=_rid(request, body), term_id=body.term_id,
                        include_ineligible=body.include_ineligible, faults=faults_of(request))


@router.post("/why-not")
def why_not(request: Request, body: WhyNotRequest):
    catalog = catalog_for(request, body.catalog_version)
    return uc.why_not(catalog, body.profile.to_domain(), body.course_ids,
                      body.weights.as_mapping() if body.weights else None, request_id=_rid(request, body))


@router.post("/simulations")
def simulations(request: Request, body: SimulationRequest):
    catalog = catalog_for(request, body.catalog_version)
    return uc.simulate(catalog, body.profile.to_domain(), body.weights.as_mapping() if body.weights else None,
                       body.scenario.to_domain(), baseline_version=body.baseline_version, request_id=_rid(request, body))
