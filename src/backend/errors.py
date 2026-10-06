"""Map domain/transport errors to the contract error envelope {request_id, contract_version, error}."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import CONTRACT_VERSION
from .application.recommend import UnknownCourses
from .domain.catalog import CatalogInvalid, CatalogUnavailable, CatalogVersionUnknown
from .domain.profile import ProfileInvalid
from .domain.ranking import InvalidWeights
from .domain.simulation import InvalidScenario

log = logging.getLogger("ai07")


def request_id_of(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if not rid:
        rid = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = rid
    return rid


def error_response(request: Request, status: int, code: str, message: str, *, retryable: bool = False,
                   details: dict | None = None) -> JSONResponse:
    error = {"code": code, "message": message, "retryable": retryable}
    if details:
        error["details"] = details
    rid = request_id_of(request)
    return JSONResponse(status_code=status, content={"request_id": rid, "contract_version": CONTRACT_VERSION, "error": error},
                        headers={"X-Request-ID": rid})


def install(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if any(e.get("type") == "json_invalid" for e in errors):
            return error_response(request, 400, "MALFORMED_JSON", "Request body is not valid JSON.")
        if isinstance(exc.body, dict) and isinstance(exc.body.get("request_id"), str):
            request.state.request_id = exc.body["request_id"]
        # Never echo input values back (they may contain profile data).
        fields = [{"field": ".".join(str(p) for p in e.get("loc", ()) if p != "body"), "message": e.get("msg", "")} for e in errors]
        return error_response(request, 422, "VALIDATION_ERROR", "Request failed validation.", details={"errors": fields})

    @app.exception_handler(ProfileInvalid)
    async def _profile(request: Request, exc: ProfileInvalid):
        return error_response(request, 422, "PROFILE_INVALID", "Profile is inconsistent with the catalog.",
                              details={"errors": [e.as_dict() for e in exc.errors]})

    @app.exception_handler(InvalidWeights)
    async def _weights(request: Request, exc: InvalidWeights):
        return error_response(request, 422, "INVALID_WEIGHTS", str(exc))

    @app.exception_handler(InvalidScenario)
    async def _scenario(request: Request, exc: InvalidScenario):
        return error_response(request, 422, "INVALID_SCENARIO", str(exc), details={"field": exc.field})

    @app.exception_handler(UnknownCourses)
    async def _unknown(request: Request, exc: UnknownCourses):
        return error_response(request, 422, "UNKNOWN_COURSE", "Unknown course IDs.", details={"course_ids": exc.course_ids})

    @app.exception_handler(CatalogVersionUnknown)
    async def _version(request: Request, exc: CatalogVersionUnknown):
        return error_response(request, 409, "CATALOG_VERSION_UNKNOWN", "Unknown or stale catalog version; refresh and retry.",
                              details={"requested": exc.requested, "available_versions": exc.available})

    @app.exception_handler(CatalogInvalid)
    async def _invalid(request: Request, exc: CatalogInvalid):
        return error_response(request, 409, "CATALOG_INVALID", "Catalog snapshot failed integrity checks.",
                              details={"catalog_version": exc.catalog_version})

    @app.exception_handler(CatalogUnavailable)
    async def _unavailable(request: Request, exc: CatalogUnavailable):
        return error_response(request, 503, "CATALOG_UNAVAILABLE", "The requested catalog snapshot is unavailable.",
                              retryable=True, details={"catalog_version": str(exc)})

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return error_response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        log.exception("unhandled error request_id=%s", request_id_of(request))  # no payload logged
        return error_response(request, 500, "INTERNAL_ERROR", "Unexpected server error.")
