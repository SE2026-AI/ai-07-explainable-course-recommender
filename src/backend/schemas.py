"""Request DTOs mirroring docs/architecture/contracts/openapi.yaml (contract 0.1.0) and their domain mapping."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import CONTRACT_VERSION
from .domain.profile import HistoryRecord as DomainHistory
from .domain.profile import StudentProfile, WorkloadPreference as DomainWorkload
from .domain.simulation import Scenario

CourseId = Field(pattern=r"^[A-Z0-9_-]+$")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class HistoryRecord(Strict):
    course_id: str = CourseId
    state: Literal["passed", "failed", "planned"]
    grade: float | None = Field(default=None, ge=0, le=10)
    completed_term: str | None = None
    source_record_id: str | None = None


class WorkloadPreference(Strict):
    hours_per_week_budget: float = Field(gt=0, le=168)
    direction: Literal["lower", "higher", "neutral"]


class Profile(Strict):
    profile_id: str = Field(min_length=1)
    history: list[HistoryRecord]
    career_goal_ids: list[str]
    interest_ids: list[str]
    workload_preference: WorkloadPreference
    max_credits_per_term: int = Field(ge=1, le=60)
    excluded_course_ids: list[str] = []

    def to_domain(self) -> StudentProfile:
        return StudentProfile(
            profile_id=self.profile_id,
            history=tuple(DomainHistory(h.course_id, h.state, h.grade, h.completed_term) for h in self.history),
            career_goal_ids=tuple(dict.fromkeys(self.career_goal_ids)),
            interest_ids=tuple(dict.fromkeys(self.interest_ids)),
            workload_preference=DomainWorkload(self.workload_preference.hours_per_week_budget, self.workload_preference.direction),
            max_credits_per_term=self.max_credits_per_term,
            excluded_course_ids=tuple(dict.fromkeys(self.excluded_course_ids)),
        )


class Weights(Strict):
    goal_match: float | None = Field(default=None, ge=0, le=1)
    interest_match: float | None = Field(default=None, ge=0, le=1)
    preparation: float | None = Field(default=None, ge=0, le=1)
    workload_fit: float | None = Field(default=None, ge=0, le=1)

    def as_mapping(self) -> dict[str, float]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class BaseRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    contract_version: Literal[CONTRACT_VERSION]  # type: ignore[valid-type]
    catalog_version: str = Field(min_length=1)
    request_id: str | None = None
    profile: Profile


class RecommendationRequest(BaseRequest):
    weights: Weights | None = None
    term_id: str | None = None
    include_ineligible: bool = True


class WhyNotRequest(BaseRequest):
    course_ids: list[str] = Field(min_length=1)
    weights: Weights | None = None


class ScenarioBody(Strict):
    scenario_id: str = Field(min_length=1)
    scenario_version: str = Field(min_length=1)
    career_goal_ids: list[str] | None = None
    interest_ids: list[str] | None = None
    weights: Weights | None = None
    workload_preference: WorkloadPreference | None = None
    selected_course_ids: list[str] | None = None
    hypothetical_passed: list[str] = []
    max_credits_per_term: int | None = Field(default=None, ge=1, le=60)
    excluded_course_ids: list[str] | None = None

    def to_domain(self) -> Scenario:
        wp = self.workload_preference
        return Scenario(
            scenario_id=self.scenario_id,
            scenario_version=self.scenario_version,
            career_goal_ids=tuple(self.career_goal_ids) if self.career_goal_ids is not None else None,
            interest_ids=tuple(self.interest_ids) if self.interest_ids is not None else None,
            weights=self.weights.as_mapping() if self.weights else None,
            workload_preference=DomainWorkload(wp.hours_per_week_budget, wp.direction) if wp else None,
            hypothetical_passed=tuple(dict.fromkeys(self.hypothetical_passed)),
            max_credits_per_term=self.max_credits_per_term,
            excluded_course_ids=tuple(self.excluded_course_ids) if self.excluded_course_ids is not None else None,
        )


class SimulationRequest(BaseRequest):
    baseline_version: str = Field(min_length=1)
    weights: Weights | None = None
    scenario: ScenarioBody
