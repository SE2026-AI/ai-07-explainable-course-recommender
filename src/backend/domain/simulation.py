"""T-08 What-if: apply a sparse scenario overlay to an immutable baseline profile and weights."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Mapping

from .catalog import CatalogSnapshot
from .profile import HistoryRecord, StudentProfile, WorkloadPreference, satisfied_course_ids


class InvalidScenario(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    scenario_version: str
    career_goal_ids: tuple[str, ...] | None = None
    interest_ids: tuple[str, ...] | None = None
    weights: Mapping[str, float] | None = None
    workload_preference: WorkloadPreference | None = None
    hypothetical_passed: tuple[str, ...] = ()
    max_credits_per_term: int | None = None
    excluded_course_ids: tuple[str, ...] | None = None


def apply_scenario(profile: StudentProfile, catalog: CatalogSnapshot, scenario: Scenario) -> StudentProfile:
    """Return a NEW profile; the baseline object is never mutated (frozen dataclasses)."""
    if not scenario.scenario_id or not scenario.scenario_version:
        raise InvalidScenario("scenario", "scenario_id và scenario_version là bắt buộc.")
    satisfied = satisfied_course_ids(profile)
    extra: list[HistoryRecord] = []
    for cid in scenario.hypothetical_passed:
        if cid not in catalog.courses:
            raise InvalidScenario("scenario.hypothetical_passed", f"Môn {cid} không có trong catalog.")
        if cid in satisfied:
            raise InvalidScenario("scenario.hypothetical_passed", f"Môn {cid} đã qua trong baseline.")
        extra.append(HistoryRecord(cid, "passed", 10.0, "hypothetical"))
    history = tuple(r for r in profile.history if r.course_id not in scenario.hypothetical_passed) + tuple(extra)
    return replace(
        profile,
        history=history,
        career_goal_ids=scenario.career_goal_ids if scenario.career_goal_ids is not None else profile.career_goal_ids,
        interest_ids=scenario.interest_ids if scenario.interest_ids is not None else profile.interest_ids,
        workload_preference=scenario.workload_preference or profile.workload_preference,
        max_credits_per_term=scenario.max_credits_per_term or profile.max_credits_per_term,
        excluded_course_ids=scenario.excluded_course_ids if scenario.excluded_course_ids is not None else profile.excluded_course_ids,
    )


def digest(obj) -> str:
    """Stable sha256 over a JSON-serializable structure (used for baseline immutability and cohort IDs)."""
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=_default)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _default(o):
    if hasattr(o, "__dataclass_fields__"):
        return {k: getattr(o, k) for k in o.__dataclass_fields__}
    if isinstance(o, Mapping):
        return dict(o)
    raise TypeError(type(o))
