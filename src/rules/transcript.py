"""Build an in-memory student record from a manually entered transcript."""

from collections.abc import Mapping
from numbers import Real
from typing import Any

import pandas as pd


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, pd.DataFrame):
        return value.to_dict("records")
    if isinstance(value, Mapping):
        return [dict(value)]
    if isinstance(value, pd.Series):
        return [value.to_dict()]
    if isinstance(value, (list, tuple)):
        if any(not isinstance(row, (Mapping, pd.Series)) for row in value):
            raise ValueError("courses: every row must be a mapping")
        return [dict(row) if isinstance(row, Mapping) else row.to_dict() for row in value]
    raise ValueError("courses: must be a sequence or table")


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, pd.Series):
        return value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    raise ValueError("curriculum: must be a mapping")


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{path}: must be a number")
    return float(value)


def _missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def build_student(curriculum, courses, conversions, semesters_completed, results) -> dict:
    """Construct a rules-compatible student record without I/O or input mutation.

    ``courses`` and ``conversions`` use the DataFrame shapes returned by Repository;
    ``curriculum`` is its curriculum row, and ``results`` contains one latest attempt
    per course as defined by the transcript contract.
    """
    info = _mapping(curriculum)
    curriculum_code = info.get("curriculum_code")
    if "curriculum_code" not in info and isinstance(curriculum, pd.Series):
        curriculum_code = curriculum.name
    if not isinstance(curriculum_code, str) or not curriculum_code:
        raise ValueError("curriculum.curriculum_code: is required")
    try:
        if isinstance(semesters_completed, bool) or not isinstance(semesters_completed, int):
            raise ValueError
        if not 0 <= semesters_completed <= 12:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("semesters_completed: must be an integer between 0 and 12") from None
    if not isinstance(results, (list, tuple)):
        raise ValueError("results: must be a sequence")
    if semesters_completed == 0 and results:
        raise ValueError("semesters_completed: must be greater than 0 when results are non-empty")
    if "pass_score" not in info or "max_score" not in info:
        raise ValueError("curriculum: must include pass_score and max_score")
    pass_score = _number(info["pass_score"], "curriculum.pass_score")
    max_score = _number(info["max_score"], "curriculum.max_score")

    course_rows = _records(courses)
    by_code: dict[str, dict[str, Any]] = {}
    for i, course in enumerate(course_rows):
        if not isinstance(course, Mapping) or _missing(course.get("course_code")):
            raise ValueError(f"courses[{i}].course_code: is required")
        code = str(course["course_code"])
        if code in by_code:
            raise ValueError(f"courses[{i}].course_code: duplicate course code")
        by_code[code] = dict(course)

    conversion_rows = _records(conversions)
    conversion_rows.sort(key=lambda row: float(row.get("min_score", 0)), reverse=True)
    normalized: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for i, raw in enumerate(results):
        path = f"results[{i}]"
        if not isinstance(raw, Mapping):
            raise ValueError(f"{path}: must be an object")
        result = dict(raw)
        code = result.get("course_code")
        if not isinstance(code, str) or not code:
            raise ValueError(f"{path}.course_code: must be a non-empty course code")
        if code not in by_code:
            raise ValueError(f"{path}.course_code: unknown course code")
        if code in seen:
            raise ValueError(f"{path}.course_code: duplicate course code")
        seen.add(code)
        semester = result.get("semester")
        if isinstance(semester, bool) or not isinstance(semester, int):
            raise ValueError(f"{path}.semester: must be an integer")
        if not 1 <= semester <= semesters_completed:
            raise ValueError(f"{path}.semester: must be between 1 and semesters_completed")
        has_score = "score" in result
        has_exempted = "exempted" in result
        if has_score == has_exempted:
            raise ValueError(f"{path}: must contain either score or exempted")
        exempted = has_exempted and result.get("exempted") is True
        if has_exempted and not exempted:
            raise ValueError(f"{path}.exempted: must be true")
        score = None
        letter = grade_point = None
        status = "exempted" if exempted else "failed"
        if has_score:
            score = _number(result["score"], f"{path}.score")
            if not 0 <= score <= max_score:
                raise ValueError(f"{path}.score: score is outside the allowed range")
            conversion = next((row for row in conversion_rows
                               if score >= float(row.get("min_score", float("inf")))), None)
            if conversion is None:
                raise ValueError(f"{path}.score: no grade conversion is available")
            letter = conversion.get("letter")
            grade_point = None if _missing(conversion.get("grade_point")) else float(conversion["grade_point"])
            status = "passed" if score >= pass_score else "failed"
        normalized[code] = {"semester": semester, "score": score, "letter_grade": letter,
                            "grade_point": grade_point, "status": status}

    passed = sorted(code for code, attempt in normalized.items() if attempt["status"] in {"passed", "exempted"})
    outstanding = sorted(code for code, attempt in normalized.items() if attempt["status"] == "failed")
    scores = {code: attempt["score"] for code, attempt in sorted(normalized.items())
              if attempt["score"] is not None}
    latest = {code: dict(attempt) for code, attempt in sorted(normalized.items())}

    earned = outstanding_credits = gpa_numerator = gpa_denominator = 0.0
    gpa_has_value = False
    blocks: dict[str, dict[str, Any]] = {}
    for course in course_rows:
        block_code = course.get("block_code")
        if block_code is not None and not _missing(block_code):
            key = str(block_code)
            blocks.setdefault(key, {"block_code": key,
                                    "required_credits": int(course.get("block_required_credits", 0) or 0),
                                    "earned_credits": 0.0,
                                    "counts_toward_total": bool(course.get("counts_toward_total", True))})
    for code, attempt in normalized.items():
        course = by_code[code]
        credits = float(course.get("credits", 0) or 0)
        counts = bool(course.get("counts_toward_total", True))
        if counts and attempt["status"] in {"passed", "exempted"}:
            earned += credits
        if counts and attempt["status"] == "failed":
            outstanding_credits += credits
        if counts and attempt["status"] in {"passed", "failed"}:
            gpa_denominator += credits
            if attempt["grade_point"] is not None:
                gpa_numerator += credits * attempt["grade_point"]
                gpa_has_value = True
        block_code = course.get("block_code")
        if block_code is not None and not _missing(block_code):
            key = str(block_code)
            item = blocks[key]
            if attempt["status"] in {"passed", "exempted"}:
                item["earned_credits"] += credits

    warnings = []
    for result in results:
        code = result["course_code"]
        attempt = normalized[code]
        if attempt["status"] not in {"passed", "exempted"}:
            continue
        groups = by_code[code].get("prerequisite_groups", []) or []
        missing_groups = [list(group) for group in groups if not (set(group) & set(passed))]
        if missing_groups:
            warnings.append({"code": "prerequisite_not_in_transcript", "course_code": code,
                             "data": {"missing_prerequisites": missing_groups}})
        for group in groups:
            for prerequisite in group:
                prior_attempt = normalized.get(prerequisite)
                if prior_attempt and prior_attempt["status"] in {"passed", "exempted"} \
                        and attempt["semester"] <= prior_attempt["semester"]:
                    warnings.append({"code": "studied_before_prerequisite", "course_code": code,
                                     "data": {"semester": attempt["semester"], "prerequisite_code": prerequisite,
                                              "prerequisite_semester": prior_attempt["semester"]}})

    return {
        "student_id": None,
        "university_code": info.get("university_code"),
        "curriculum_code": curriculum_code,
        "semesters_completed": semesters_completed,
        "target_semester": semesters_completed + 1,
        "passed_courses": passed,
        "outstanding_courses": outstanding,
        "latest_scores": scores,
        "latest_attempts": latest,
        "credits_earned": int(earned),
        "credits_outstanding": int(outstanding_credits),
        "gpa": round(gpa_numerator / gpa_denominator, 2) if gpa_denominator and gpa_has_value else None,
        "blocks": [dict(block, earned_credits=int(block["earned_credits"]))
                   for block in blocks.values() if block["earned_credits"] > 0],
        "block_progress": {key: dict(block, earned_credits=int(block["earned_credits"]))
                           for key, block in blocks.items()},
        "warnings": warnings,
    }
