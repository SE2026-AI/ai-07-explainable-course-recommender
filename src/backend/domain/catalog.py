"""T-03 Catalog: immutable, versioned snapshot validated before any eligibility claim."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

COURSE_ID_PATTERN = re.compile(r"^[A-Z0-9_-]+$")


class CatalogInvalid(Exception):
    """Snapshot has duplicate IDs, dangling references, cycles or bad values; no results may be produced."""

    def __init__(self, catalog_version: str, problems: list[str]):
        super().__init__(f"catalog {catalog_version} invalid: {'; '.join(problems)}")
        self.catalog_version = catalog_version
        self.problems = problems


class CatalogUnavailable(Exception):
    """Catalog source cannot be read; callers must not fabricate personalized results."""


class CatalogVersionUnknown(Exception):
    def __init__(self, requested: str, available: list[str]):
        super().__init__(f"unknown catalog version {requested!r}")
        self.requested = requested
        self.available = available


@dataclass(frozen=True)
class Course:
    course_id: str
    title: str
    credits: int
    workload_hours_per_week: float | None
    mandatory_prerequisites: tuple[str, ...]
    recommended_preparation: tuple[str, ...]
    available_terms: tuple[str, ...]
    topics: tuple[str, ...]
    goal_relevance: Mapping[str, float] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class CatalogSnapshot:
    catalog_version: str
    as_of: str
    source: str
    courses: Mapping[str, Course]
    goals: Mapping[str, str]  # goal_id -> title

    @property
    def topics(self) -> list[str]:
        return sorted({t for c in self.courses.values() for t in c.topics})

    def edges(self) -> list[tuple[str, str]]:
        """Prerequisite -> dependent, sorted for stable output."""
        return sorted((p, c.course_id) for c in self.courses.values() for p in c.mandatory_prerequisites)

    def dependents(self, course_id: str) -> list[str]:
        return sorted(c.course_id for c in self.courses.values() if course_id in c.mandatory_prerequisites)


def build_snapshot(raw: Mapping) -> CatalogSnapshot:
    """Parse and validate a raw catalog document. Raises CatalogInvalid on any integrity problem."""
    version = str(raw.get("catalog_version") or "")
    problems: list[str] = []
    if not version:
        problems.append("missing catalog_version")
    goals = dict(raw.get("goals") or {})
    courses: dict[str, Course] = {}
    for item in raw.get("courses") or []:
        cid = item.get("course_id", "")
        if not COURSE_ID_PATTERN.match(cid or ""):
            problems.append(f"invalid course_id {cid!r}")
            continue
        if cid in courses:
            problems.append(f"duplicate course_id {cid}")
            continue
        credits = item.get("credits")
        if not isinstance(credits, int) or isinstance(credits, bool) or credits < 1:
            problems.append(f"{cid}: credits must be a positive integer")
        hours = item.get("workload_hours_per_week")
        if hours is not None and (not isinstance(hours, (int, float)) or not math.isfinite(hours) or hours < 0):
            problems.append(f"{cid}: workload_hours_per_week must be a nonnegative number")
        relevance = dict(item.get("goal_relevance") or {})
        for goal_id, value in relevance.items():
            if goal_id not in goals:
                problems.append(f"{cid}: goal_relevance references unknown goal {goal_id}")
            elif not isinstance(value, (int, float)) or not 0 <= value <= 1:
                problems.append(f"{cid}: goal_relevance[{goal_id}] must be within [0,1]")
        courses[cid] = Course(
            course_id=cid,
            title=item.get("title", cid),
            credits=credits if isinstance(credits, int) else 0,
            workload_hours_per_week=float(hours) if isinstance(hours, (int, float)) else None,
            mandatory_prerequisites=tuple(item.get("mandatory_prerequisites") or ()),
            recommended_preparation=tuple(item.get("recommended_preparation") or ()),
            available_terms=tuple(item.get("available_terms") or ()),
            topics=tuple(item.get("topics") or ()),
            goal_relevance=MappingProxyType(relevance),
            description=item.get("description", ""),
        )
    for course in courses.values():
        for ref in course.mandatory_prerequisites + course.recommended_preparation:
            if ref not in courses:
                problems.append(f"{course.course_id} references unknown course {ref}")
            elif ref == course.course_id:
                problems.append(f"{course.course_id} references itself")
    if not problems:
        cycle = _find_cycle(courses)
        if cycle:
            problems.append("prerequisite cycle: " + " -> ".join(cycle))
    if problems:
        raise CatalogInvalid(version or "<unknown>", problems)
    return CatalogSnapshot(
        catalog_version=version,
        as_of=str(raw.get("as_of", "")),
        source=str(raw.get("source", "")),
        courses=MappingProxyType(courses),
        goals=MappingProxyType(goals),
    )


def _find_cycle(courses: Mapping[str, Course]) -> list[str] | None:
    state: dict[str, int] = {}  # 1 = on stack, 2 = done
    stack: list[str] = []

    def visit(cid: str) -> list[str] | None:
        state[cid] = 1
        stack.append(cid)
        for pre in courses[cid].mandatory_prerequisites:
            if state.get(pre) == 1:
                return stack[stack.index(pre):] + [pre]
            if state.get(pre) is None:
                found = visit(pre)
                if found:
                    return found
        stack.pop()
        state[cid] = 2
        return None

    for cid in sorted(courses):
        if state.get(cid) is None:
            found = visit(cid)
            if found:
                return found
    return None
