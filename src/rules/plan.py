"""Validation rules for a proposed one-term study plan."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from src.rules.status import elective_credits_passed, fits_in_block


def _value(course: Mapping[str, Any] | pd.Series, key: str, default: Any = None) -> Any:
    """Read an optional course field while treating pandas' NaN as absent."""
    value = course.get(key, default)
    return default if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)) else value


def term_credits(course: Mapping[str, Any] | pd.Series) -> int:
    """Credits one course takes up in a term's total (contract 6.7, 6.11, 6.12): all of its credits.

    This is the single place of that rule. A block that does not count toward the graduation
    total (soft skills, HUS1012) still takes up the term's load, so ``counts_toward_total`` is
    deliberately ignored here: it only affects graduation progress and GPA. Plan checking, the
    credit-window selection of the ranking layer and the synthetic data generator all call this,
    so a recommended list always has the same total when it is checked as a plan.
    """
    return int(course["credits"])


def credits_to_graduate(curriculum: Mapping[str, Any] | pd.Series,
                        student: Mapping[str, Any] | pd.Series) -> int | None:
    """Credits still missing to graduate: the curriculum's ``total_credits`` minus the student's
    ``credits_earned``, never below 0. ``None`` when the student row carries no ``credits_earned``.

    In a student's last term this can be below ``min_credits``, and then the term cannot (and need
    not) reach that minimum. Contract 6.11 lowers its credit floor to this number; contract 6.12
    should use the same function for ``credit_below_minimum``. ``credits_earned`` only counts blocks
    that count toward the graduation total, exactly like ``total_credits``.
    """
    earned = _value(student, "credits_earned")
    if earned is None:
        return None
    return max(0, int(curriculum["total_credits"]) - int(earned))


def plan_total_credits(courses: pd.DataFrame, course_codes: Sequence[str]) -> int:
    """Credits a one-term plan takes up (contract 6.7): ``term_credits()`` of each curriculum
    course once, whatever its block and however often it is listed. Unknown codes add nothing."""
    by_code = {str(row["course_code"]): row for row in courses.to_dict("records")}
    return sum(term_credits(by_code[code]) for code in dict.fromkeys(course_codes) if code in by_code)


def check_plan(repo: Any, student: Mapping[str, Any] | pd.Series,
               course_codes: Sequence[str], min_credits=None, max_credits=None) -> list[dict[str, Any]]:
    """Return all rule violations for ``course_codes`` in their supplied order.

    Prerequisites are checked against courses already passed by the student. Courses in
    this plan never satisfy prerequisites for another planned course.
    """
    if not course_codes and min_credits is None:
        return []
    curriculum_code = student["curriculum_code"]
    courses = repo.curriculum_courses(curriculum_code)
    by_code = {str(row["course_code"]): row for _, row in courses.iterrows()}
    passed = set(student["passed_courses"])
    curriculum = repo.curriculum(curriculum_code)
    configured_max = int(curriculum["max_credits_per_term"])
    maximum = max_credits if max_credits is not None else configured_max
    seen: set[str] = set()
    violations: list[tuple[int, str, dict[str, Any]]] = []

    # Associate plan-wide limit violations with the first course occurrence that
    # takes the cumulative total over the limit, while reporting the final total.
    # Same total as plan_total_credits(): term_credits() of every known course, once.
    total_credits = 0
    total_crossing: int | None = None
    counted_total_codes: set[str] = set()
    for index, code in enumerate(course_codes):
        course = by_code.get(code)
        if course is not None and code not in counted_total_codes:
            total_credits += term_credits(course)
            counted_total_codes.add(code)
            if total_crossing is None and total_credits > maximum:
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
            ("max_credits" if max_credits is not None else "max_credits_per_term"): maximum,
            "total_credits": total_credits,
        }))

    violations.sort(key=lambda item: (item[0], item[1]))
    result = [{"code": code, "course_code": course_codes[index] if index >= 0 else None, "data": data}
              for index, code, data in violations]

    # Explicit caller minimum is independent and always appears last.
    if min_credits is not None and total_credits < min_credits:
        result.append({"code": "credit_below_minimum", "course_code": None,
                       "data": {"min_credits": min_credits, "total_credits": total_credits}})
    return result
