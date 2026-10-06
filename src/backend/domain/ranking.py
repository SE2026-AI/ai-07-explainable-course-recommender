"""T-06 Ranking: deterministic weighted scoring over four normalized components (ADR-001).

The score is suitability, not a probability of success. Eligibility is decided before ranking.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Mapping

from .catalog import Course, CatalogSnapshot
from .profile import StudentProfile

ALGORITHM_VERSION = "rank-0.1"
NORMALIZATION_POLICY = "renormalize-over-available-components"
COMPONENTS = ("goal_match", "interest_match", "preparation", "workload_fit")
DEFAULT_WEIGHTS = {"goal_match": 0.50, "interest_match": 0.20, "preparation": 0.10, "workload_fit": 0.20}


class InvalidWeights(ValueError):
    pass


class RankingFailure(RuntimeError):
    """Ranking could not be computed; callers must not invent scores."""


@dataclass(frozen=True)
class ComponentScore:
    value: float | None
    weight: float  # normalized requested weight
    effective_weight: float  # renormalized over available components
    contribution: float
    available: bool


@dataclass(frozen=True)
class ScoredCourse:
    course_id: str
    total: float | None  # None => NO_SCORABLE_COMPONENTS
    components: Mapping[str, ComponentScore]
    rank: int | None = None

    @property
    def missing_components(self) -> list[str]:
        return [name for name, c in self.components.items() if not c.available]


def normalize_weights(weights: Mapping[str, float] | None) -> dict[str, float]:
    """Validate and normalize to sum 1. Missing keys mean weight 0; None means defaults."""
    if weights is None:
        weights = DEFAULT_WEIGHTS
    unknown = set(weights) - set(COMPONENTS)
    if unknown:
        raise InvalidWeights(f"unknown components: {', '.join(sorted(unknown))}")
    values = {}
    for name in COMPONENTS:
        raw = weights.get(name, 0.0)
        if raw is None:
            raw = 0.0
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            raise InvalidWeights(f"{name} must be a finite number")
        if raw < 0:
            raise InvalidWeights(f"{name} must be nonnegative")
        values[name] = float(raw)
    total = sum(values.values())
    if total <= 0:
        raise InvalidWeights("at least one weight must be positive")
    return {name: v / total for name, v in values.items()}


def component_values(course: Course, profile: StudentProfile, satisfied: set[str]) -> dict[str, float | None]:
    """Raw component values in [0,1]; None = unavailable (never guessed)."""
    return {
        "goal_match": _goal_match(course, profile),
        "interest_match": _interest_match(course, profile),
        "preparation": _preparation(course, satisfied),
        "workload_fit": workload_fit(course.workload_hours_per_week, profile.workload_preference.hours_per_week_budget,
                                     profile.workload_preference.direction),
    }


def _goal_match(course: Course, profile: StudentProfile) -> float | None:
    # Explicit goal -> course relevance map maintained in the catalog; never inferred from titles.
    if not profile.career_goal_ids:
        return None
    return max(course.goal_relevance.get(g, 0.0) for g in profile.career_goal_ids)


def _interest_match(course: Course, profile: StudentProfile) -> float | None:
    if not profile.interest_ids or not course.topics:
        return None
    interests, topics = set(profile.interest_ids), set(course.topics)
    return len(interests & topics) / len(interests | topics)


def _preparation(course: Course, satisfied: set[str]) -> float | None:
    if not course.recommended_preparation:
        return None
    done = sum(1 for p in course.recommended_preparation if p in satisfied)
    return done / len(course.recommended_preparation)


def workload_fit(hours: float | None, budget: float | None, direction: str) -> float | None:
    if hours is None or not budget or budget <= 0:
        return None
    if direction == "lower":
        return max(0.0, 1 - hours / budget)
    if direction == "higher":
        return min(1.0, hours / budget)
    if hours <= budget:
        return 1.0
    return max(0.0, 1 - (hours - budget) / budget)


def score(course_id: str, values: Mapping[str, float | None], weights: Mapping[str, float]) -> ScoredCourse:
    """Weighted sum renormalized over available components. `weights` must already be normalized."""
    available_weight = sum(weights[n] for n in COMPONENTS if values.get(n) is not None)
    components: dict[str, ComponentScore] = {}
    total = 0.0
    for name in COMPONENTS:
        value = values.get(name)
        if value is None or available_weight <= 0:
            components[name] = ComponentScore(value, weights[name], 0.0, 0.0, value is not None)
            continue
        effective = weights[name] / available_weight
        contribution = effective * value
        total += contribution
        components[name] = ComponentScore(value, weights[name], effective, contribution, True)
    return ScoredCourse(course_id, total if available_weight > 0 else None, components)


def rank(scored: list[ScoredCourse]) -> list[ScoredCourse]:
    """Total descending (unrounded), then course_id ascending. Unscorable courses go last without rank."""
    with_score = sorted((s for s in scored if s.total is not None), key=lambda s: (-s.total, s.course_id))
    without = sorted((s for s in scored if s.total is None), key=lambda s: s.course_id)
    ranked = [ScoredCourse(s.course_id, s.total, s.components, i) for i, s in enumerate(with_score, start=1)]
    return ranked + without


def rank_courses(catalog: CatalogSnapshot, profile: StudentProfile, satisfied: set[str],
                 course_ids: list[str], weights: Mapping[str, float]) -> list[ScoredCourse]:
    scored = [score(cid, component_values(catalog.courses[cid], profile, satisfied), weights) for cid in course_ids]
    return rank(scored)


def display_percent(total: float | None) -> float | None:
    """Round half-up to one decimal percent, only for display."""
    if total is None:
        return None
    return float(Decimal(str(total * 100)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
