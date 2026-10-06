"""T-07 Explanations: deterministic templates built only from score components and catalog/profile evidence."""

from __future__ import annotations

from dataclasses import dataclass

from . import prerequisites as pre
from .catalog import CatalogSnapshot
from .profile import StudentProfile, satisfied_course_ids
from .ranking import ScoredCourse

GOAL_MATCH = "GOAL_MATCH"
INTEREST_MATCH = "INTEREST_MATCH"
PREPARATION_SIGNAL = "PREPARATION_SIGNAL"
WORKLOAD_FIT = "WORKLOAD_FIT"
WORKLOAD_MISMATCH = "WORKLOAD_MISMATCH"
LOW_RELEVANCE = "LOW_RELEVANCE"
LOWER_RANK = "LOWER_RANK"
CONDITIONALLY_UNLOCKABLE = "CONDITIONALLY_UNLOCKABLE"
NO_SCORABLE_COMPONENTS = "NO_SCORABLE_COMPONENTS"

REASON_CODES = frozenset({
    GOAL_MATCH, INTEREST_MATCH, PREPARATION_SIGNAL, WORKLOAD_FIT, WORKLOAD_MISMATCH, LOW_RELEVANCE, LOWER_RANK,
    CONDITIONALLY_UNLOCKABLE, NO_SCORABLE_COMPONENTS, pre.COMPLETED, pre.MISSING_PREREQUISITE,
    pre.TRANSITIVE_BLOCKED, pre.NOT_OFFERED, pre.EXCLUDED_BY_USER, pre.RETAKE,
})

STRONG = 0.5  # component value at or above which it is cited as a positive reason
WEAK = 0.3  # goal relevance below which LOW_RELEVANCE is reported


@dataclass(frozen=True)
class Reason:
    code: str
    text: str
    evidence_refs: tuple[tuple[str, str], ...]  # (source, record_id)
    component: str | None = None

    def as_dict(self) -> dict:
        data = {"code": self.code, "text": self.text,
                "evidence_refs": [{"source": s, "record_id": r} for s, r in self.evidence_refs]}
        if self.component:
            data["component"] = self.component
        return data


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def explain_scored(catalog: CatalogSnapshot, profile: StudentProfile, scored: ScoredCourse,
                   eligibility: pre.EligibilityResult) -> list[Reason]:
    course = catalog.courses[scored.course_id]
    src = catalog.catalog_version
    reasons: list[Reason] = []
    c = scored.components
    if scored.total is None:
        reasons.append(Reason(NO_SCORABLE_COMPONENTS, "Không đủ dữ liệu để tính điểm phù hợp cho môn này.", ((src, course.course_id),)))
    goal = c["goal_match"]
    if goal.available and goal.value is not None:
        goal_ids = [g for g in profile.career_goal_ids if course.goal_relevance.get(g, 0.0) == goal.value]
        refs = ((src, course.course_id),) + tuple((src, f"goal:{g}") for g in goal_ids[:1])
        if goal.value >= STRONG and goal_ids:
            reasons.append(Reason(GOAL_MATCH, f"Phù hợp mục tiêu {catalog.goals[goal_ids[0]]} (mức liên quan {_pct(goal.value)}, đóng góp {_pct(goal.contribution)} vào điểm).", refs, "goal_match"))
        elif goal.value < WEAK:
            reasons.append(Reason(LOW_RELEVANCE, f"Ít liên quan tới mục tiêu đã chọn (mức liên quan {_pct(goal.value)}, ngưỡng {_pct(WEAK)}).", refs, "goal_match"))
    interest = c["interest_match"]
    if interest.available and interest.value and interest.value > 0:
        shared = sorted(set(profile.interest_ids) & set(course.topics))
        reasons.append(Reason(INTEREST_MATCH, f"Trùng sở thích: {', '.join(shared)} (đóng góp {_pct(interest.contribution)}).",
                              ((src, course.course_id),) + tuple(("profile", f"interest:{t}") for t in shared), "interest_match"))
    prep = c["preparation"]
    if prep.available and prep.value and prep.value > 0:
        done = [p for p in course.recommended_preparation if p in satisfied_course_ids(profile)]
        reasons.append(Reason(PREPARATION_SIGNAL, f"Đã học môn nên chuẩn bị trước: {', '.join(done)}.",
                              tuple(("profile", f"history:{p}") for p in done) + ((src, course.course_id),), "preparation"))
    work = c["workload_fit"]
    if work.available and work.value is not None:
        hours, budget = course.workload_hours_per_week, profile.workload_preference.hours_per_week_budget
        refs = ((src, course.course_id), ("profile", "workload_preference"))
        if work.value >= STRONG:
            reasons.append(Reason(WORKLOAD_FIT, f"Khối lượng ~{hours:g} giờ/tuần, hợp với ngân sách {budget:g} giờ/tuần.", refs, "workload_fit"))
        else:
            reasons.append(Reason(WORKLOAD_MISMATCH, f"Khối lượng ~{hours:g} giờ/tuần, chưa hợp với ngân sách {budget:g} giờ/tuần (độ phù hợp {_pct(work.value)}).", refs, "workload_fit"))
    if eligibility.unlocks:
        reasons.append(Reason(CONDITIONALLY_UNLOCKABLE, f"Qua môn này sẽ mở khóa: {', '.join(eligibility.unlocks)}.",
                              tuple((src, u) for u in eligibility.unlocks)))
    if pre.RETAKE in eligibility.reason_codes:
        reasons.append(Reason(pre.RETAKE, "Bạn từng chưa đạt môn này; có thể đăng ký học lại.", (("profile", f"history:{course.course_id}"),)))
    return reasons


def explain_blocked(catalog: CatalogSnapshot, eligibility: pre.EligibilityResult, term_id: str | None = None) -> list[Reason]:
    src = catalog.catalog_version
    cid = eligibility.course_id
    reasons: list[Reason] = []
    for code in eligibility.reason_codes:
        if code == pre.COMPLETED:
            reasons.append(Reason(code, f"Bạn đã qua môn {cid}.", (("profile", f"history:{cid}"),)))
        elif code == pre.MISSING_PREREQUISITE:
            missing = eligibility.direct_missing_prerequisite_ids
            reasons.append(Reason(code, f"Chưa qua môn tiên quyết bắt buộc: {', '.join(missing)}.", ((src, cid),) + tuple((src, m) for m in missing)))
        elif code == pre.TRANSITIVE_BLOCKED:
            chains = "; ".join(" → ".join(p) for p in eligibility.transitive_missing_paths if len(p) > 2)
            reasons.append(Reason(code, f"Cần học theo chuỗi: {chains}.", tuple((src, x) for p in eligibility.transitive_missing_paths for x in p[:-1])))
        elif code == pre.NOT_OFFERED:
            reasons.append(Reason(code, f"Môn {cid} không mở trong kỳ {term_id}.", ((src, cid),)))
        elif code == pre.EXCLUDED_BY_USER:
            reasons.append(Reason(code, f"Bạn đã chọn loại môn {cid}.", (("profile", f"excluded:{cid}"),)))
    return reasons


def explain_lower_rank(scored: ScoredCourse, top: ScoredCourse, cohort_size: int) -> Reason:
    gap = (top.total or 0) - (scored.total or 0)
    return Reason(LOWER_RANK, f"Đủ điều kiện nhưng xếp hạng {scored.rank}/{cohort_size}, thấp hơn {top.course_id} {_pct(gap)} điểm.",
                  (("ranking", scored.course_id), ("ranking", top.course_id)))


def verify_evidence(reasons: list[Reason], catalog: CatalogSnapshot, profile: StudentProfile) -> tuple[list[Reason], list[str]]:
    """Drop any reason whose evidence does not resolve; return kept reasons and dropped codes (degraded)."""
    valid_profile = ({f"history:{r.course_id}" for r in profile.history}
                     | {f"interest:{i}" for i in profile.interest_ids}
                     | {f"excluded:{c}" for c in profile.excluded_course_ids} | {"workload_preference"})
    kept, dropped = [], []
    for reason in reasons:
        ok = reason.code in REASON_CODES and reason.evidence_refs
        for source, record in reason.evidence_refs:
            if source == catalog.catalog_version:
                ok = ok and (record in catalog.courses or (record.startswith("goal:") and record[5:] in catalog.goals))
            elif source == "profile":
                ok = ok and record in valid_profile
            elif source != "ranking":
                ok = False
        (kept if ok else dropped).append(reason)
    return kept, [r.code for r in dropped]
