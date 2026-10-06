"""T-05 Prerequisite validation: mandatory prerequisites are AND gates satisfied only by earlier passes."""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import CatalogSnapshot

# Reason codes for course disposition
COMPLETED = "COMPLETED"
MISSING_PREREQUISITE = "MISSING_PREREQUISITE"
TRANSITIVE_BLOCKED = "TRANSITIVE_BLOCKED"
NOT_OFFERED = "NOT_OFFERED"
EXCLUDED_BY_USER = "EXCLUDED_BY_USER"
RETAKE = "RETAKE"


@dataclass(frozen=True)
class EligibilityResult:
    course_id: str
    eligible: bool
    direct_missing_prerequisite_ids: tuple[str, ...] = ()
    transitive_missing_paths: tuple[tuple[str, ...], ...] = ()
    reason_codes: tuple[str, ...] = ()
    unlocks: tuple[str, ...] = field(default=())  # courses that become eligible once this one is passed


def evaluate(
    catalog: CatalogSnapshot,
    satisfied: set[str],
    course_id: str,
    *,
    term_id: str | None = None,
    excluded: set[str] | frozenset[str] = frozenset(),
    failed: set[str] | frozenset[str] = frozenset(),
) -> EligibilityResult:
    """Eligibility of one course for the next term given courses already passed (`satisfied`)."""
    course = catalog.courses[course_id]
    if course_id in satisfied:
        return EligibilityResult(course_id, False, reason_codes=(COMPLETED,))
    reasons: list[str] = []
    if course_id in excluded:
        reasons.append(EXCLUDED_BY_USER)
    if term_id and course.available_terms and term_id not in course.available_terms:
        reasons.append(NOT_OFFERED)
    missing = tuple(p for p in course.mandatory_prerequisites if p not in satisfied)
    paths: tuple[tuple[str, ...], ...] = ()
    if missing:
        reasons.append(MISSING_PREREQUISITE)
        paths = tuple(_missing_paths(catalog, satisfied, course_id))
        if any(len(p) > 2 for p in paths):
            reasons.append(TRANSITIVE_BLOCKED)
    eligible = not reasons
    if course_id in failed:
        reasons.append(RETAKE)  # adopted policy: a failed course may be retaken when its own gates pass
    unlocks = tuple(unlocked_by(catalog, satisfied, course_id)) if eligible else ()
    return EligibilityResult(course_id, eligible, missing, paths, tuple(reasons), unlocks)


def _missing_paths(catalog: CatalogSnapshot, satisfied: set[str], course_id: str) -> list[tuple[str, ...]]:
    """Chains from the nearest takeable missing ancestor to `course_id`, e.g. ST201 -> AI301 -> DL401."""
    paths: list[tuple[str, ...]] = []
    for pre in catalog.courses[course_id].mandatory_prerequisites:
        if pre in satisfied:
            continue
        sub = _missing_paths(catalog, satisfied, pre)
        if sub:
            paths.extend(path + (course_id,) for path in sub)
        else:
            paths.append((pre, course_id))
    return sorted(set(paths))


def unlocked_by(catalog: CatalogSnapshot, satisfied: set[str], course_id: str) -> list[str]:
    """Dependents whose only missing prerequisite is `course_id` (conditional unlock after passing it)."""
    result = []
    for dep in catalog.dependents(course_id):
        if dep in satisfied:
            continue
        missing = [p for p in catalog.courses[dep].mandatory_prerequisites if p not in satisfied]
        if missing == [course_id]:
            result.append(dep)
    return result


def eligible_now(catalog: CatalogSnapshot, satisfied: set[str], **kwargs) -> list[str]:
    return sorted(cid for cid in catalog.courses if evaluate(catalog, satisfied, cid, **kwargs).eligible)
