"""Validation rules for a proposed one-term study plan."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from src.rules.status import elective_credits_passed, fits_in_block


def _value(course: Mapping[str, Any] | pd.Series, key: str, default: Any = None) -> Any:
    """Read an optional course field while treating pandas' NaN as absent."""
    value = course.get(key, default)
    return default if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)) else value


def check_plan(repo: Any, student: Mapping[str, Any] | pd.Series,
               course_codes: Sequence[str]) -> list[dict[str, Any]]:
    """Return all rule violations for ``course_codes`` in their supplied order.

    Prerequisites are checked against courses already passed by the student. Courses in
    this plan never satisfy prerequisites for another planned course.
    """
    if not course_codes:
        return []

    curriculum_code = student["curriculum_code"]
    courses = repo.curriculum_courses(curriculum_code)
    by_code = {str(row["course_code"]): row for _, row in courses.iterrows()}
    passed = set(student["passed_courses"])
    curriculum = repo.curriculum(curriculum_code)
    max_credits = int(curriculum["max_credits_per_term"])
    seen: set[str] = set()
    violations: list[tuple[int, str, dict[str, Any]]] = []

    # Associate plan-wide limit violations with the first course occurrence that
    # takes the cumulative total over the limit, while reporting the final total.
    total_credits = 0
    total_crossing: int | None = None
    for index, code in enumerate(course_codes):
        course = by_code.get(code)
        if course is not None and bool(_value(course, "counts_toward_total", True)):
            total_credits += int(course["credits"])
            if total_crossing is None and total_credits > max_credits:
                total_crossing = index

    blocks = repo.elective_blocks(curriculum_code)
    required_by_block = {str(row["block_code"]): int(row["required_credits"])
                         for _, row in blocks.iterrows()}
    earned_by_block = elective_credits_passed(courses, passed)
    planned_by_block = {block: earned for block, earned in earned_by_block.items()}
    counted_block_courses = set(passed)
    for index, code in enumerate(course_codes):
        course = by_code.get(code)
        if code in seen:
            violations.append((index, "duplicate_course", {
                "occurrence": course_codes[:index].count(code) + 1,
            }))
        else:
            seen.add(code)

        if code in passed:
            violations.append((index, "already_passed", {}))

        if course is None:
            violations.append((index, "not_in_curriculum", {}))
            continue

        groups = _value(course, "prerequisite_groups", []) or []
        missing = [list(group) for group in groups if not (set(group) & passed)]
        if missing:
            violations.append((index, "missing_prerequisite", {"missing_prerequisites": missing}))

        block = _value(course, "elective_block")
        if block is not None and code not in counted_block_courses:
            block = str(block)
            required = required_by_block.get(block)
            if required is not None:
                credits = int(course["credits"])
                taken = planned_by_block.get(block, 0)
                if not fits_in_block(credits, taken, required):
                    violations.append((index, "block_limit_exceeded", {
                        "block_code": block,
                        "required_credits": required,
                        "earned_credits": earned_by_block.get(block, 0),
                        "planned_credits": taken - earned_by_block.get(block, 0),
                        "course_credits": credits,
                        "total_credits": taken + credits,
                    }))
                planned_by_block[block] = taken + credits
            counted_block_courses.add(code)

    if total_crossing is not None:
        violations.append((total_crossing, "credit_limit_exceeded", {
            "max_credits_per_term": max_credits,
            "total_credits": total_credits,
        }))

    violations.sort(key=lambda item: (item[0], item[1]))
    return [{"code": code, "course_code": course_codes[index], "data": data}
            for index, code, data in violations]
