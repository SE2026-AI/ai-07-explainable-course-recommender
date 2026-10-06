"""T-04 Profile: synthetic, request-scoped student profile and its validation against a catalog."""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import CatalogSnapshot

# Adopted synthetic policy (DECISIONS.md, T-00): grade scale 0-10, pass >= 5.
PASSING_GRADE = 5.0
HISTORY_STATES = ("passed", "failed", "planned")


@dataclass(frozen=True)
class HistoryRecord:
    course_id: str
    state: str
    grade: float | None = None
    completed_term: str | None = None


@dataclass(frozen=True)
class WorkloadPreference:
    hours_per_week_budget: float
    direction: str  # lower | higher | neutral


@dataclass(frozen=True)
class StudentProfile:
    profile_id: str
    history: tuple[HistoryRecord, ...]
    career_goal_ids: tuple[str, ...]
    interest_ids: tuple[str, ...]
    workload_preference: WorkloadPreference
    max_credits_per_term: int
    excluded_course_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Issue:
    field: str
    code: str
    message: str

    def as_dict(self) -> dict:
        return {"field": self.field, "code": self.code, "message": self.message}


@dataclass
class ProfileInvalid(Exception):
    errors: list[Issue]
    warnings: list[Issue] = field(default_factory=list)

    def __str__(self) -> str:
        return "; ".join(f"{e.field}: {e.code}" for e in self.errors)


def satisfied_course_ids(profile: StudentProfile) -> set[str]:
    """Courses that count for prerequisites: passed WITH a passing grade. Missing grade never implies pass."""
    return {
        r.course_id for r in profile.history
        if r.state == "passed" and r.grade is not None and r.grade >= PASSING_GRADE
    }


def failed_course_ids(profile: StudentProfile) -> set[str]:
    return {r.course_id for r in profile.history if r.state == "failed"}


def check_profile(profile: StudentProfile, catalog: CatalogSnapshot) -> tuple[list[Issue], list[Issue]]:
    """Return (errors, warnings). Errors make the profile unusable; warnings are informational."""
    errors: list[Issue] = []
    warnings: list[Issue] = []
    seen: set[str] = set()
    for i, record in enumerate(profile.history):
        where = f"profile.history[{i}]"
        if record.course_id not in catalog.courses:
            errors.append(Issue(where + ".course_id", "UNKNOWN_COURSE", f"Môn {record.course_id} không có trong catalog {catalog.catalog_version}."))
            continue
        if record.course_id in seen:
            errors.append(Issue(where + ".course_id", "DUPLICATE_HISTORY", f"Môn {record.course_id} xuất hiện nhiều lần trong lịch sử."))
        seen.add(record.course_id)
        if record.state not in HISTORY_STATES:
            errors.append(Issue(where + ".state", "INVALID_STATE", f"Trạng thái {record.state!r} không hợp lệ."))
        elif record.state == "passed":
            if record.grade is None:
                warnings.append(Issue(where + ".grade", "PASS_WITHOUT_GRADE", f"Môn {record.course_id} không có điểm nên chưa được tính là đã qua cho điều kiện tiên quyết."))
            elif record.grade < PASSING_GRADE:
                errors.append(Issue(where + ".grade", "GRADE_STATE_MISMATCH", f"Môn {record.course_id} ghi 'passed' nhưng điểm {record.grade} < {PASSING_GRADE:g}."))
        elif record.state == "failed" and record.grade is not None and record.grade >= PASSING_GRADE:
            errors.append(Issue(where + ".grade", "GRADE_STATE_MISMATCH", f"Môn {record.course_id} ghi 'failed' nhưng điểm {record.grade} >= {PASSING_GRADE:g}."))
    for i, goal_id in enumerate(profile.career_goal_ids):
        if goal_id not in catalog.goals:
            errors.append(Issue(f"profile.career_goal_ids[{i}]", "UNKNOWN_GOAL", f"Mục tiêu {goal_id} không có trong catalog."))
    topics = set(catalog.topics)
    for i, interest in enumerate(profile.interest_ids):
        if interest not in topics:
            errors.append(Issue(f"profile.interest_ids[{i}]", "UNKNOWN_INTEREST", f"Sở thích {interest} không khớp chủ đề nào trong catalog."))
    for i, cid in enumerate(profile.excluded_course_ids):
        if cid not in catalog.courses:
            errors.append(Issue(f"profile.excluded_course_ids[{i}]", "UNKNOWN_COURSE", f"Môn {cid} không có trong catalog."))
    if not errors:
        satisfied = satisfied_course_ids(profile)
        for record in profile.history:
            if record.course_id in satisfied:
                gaps = [p for p in catalog.courses[record.course_id].mandatory_prerequisites if p not in satisfied]
                if gaps:
                    # Data model: a recorded pass is never rewritten; only warn.
                    warnings.append(Issue("profile.history", "HISTORY_PREREQUISITE_GAP", f"Môn {record.course_id} đã qua nhưng lịch sử thiếu tiên quyết {', '.join(gaps)}."))
    return errors, warnings


def validate_profile(profile: StudentProfile, catalog: CatalogSnapshot) -> list[Issue]:
    """Raise ProfileInvalid on errors; return warnings otherwise."""
    errors, warnings = check_profile(profile, catalog)
    if errors:
        raise ProfileInvalid(errors, warnings)
    return warnings
