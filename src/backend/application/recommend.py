"""Recommendation, why-not and what-if use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .. import CONTRACT_VERSION
from ..domain import explanations as ex
from ..domain import prerequisites as pre
from ..domain import ranking
from ..domain.catalog import CatalogSnapshot
from ..domain.profile import (Issue, ProfileInvalid, StudentProfile, failed_course_ids, satisfied_course_ids,
                              validate_profile)
from ..domain.simulation import InvalidScenario, Scenario, apply_scenario, digest

# Fault names accepted by the reliability harness (RELIABILITY.md); never enabled by default.
RANKING_FAILURE = "ranking_failure"
EXPLANATION_FAILURE = "explanation_failure"


class UnknownCourses(ValueError):
    def __init__(self, course_ids: list[str]):
        super().__init__(", ".join(course_ids))
        self.course_ids = course_ids


@dataclass
class Evaluation:
    """Intermediate result shared by recommendation, why-not and simulation."""
    eligibility: dict[str, pre.EligibilityResult]
    ranked: list[ranking.ScoredCourse] | None  # None => ranking unavailable
    weights: dict[str, float]
    satisfied: set[str]
    candidate_set_id: str


def evaluate(catalog: CatalogSnapshot, profile: StudentProfile, weights: Mapping[str, float] | None,
             term_id: str | None = None, faults: frozenset[str] = frozenset()) -> Evaluation:
    normalized = ranking.normalize_weights(weights)
    satisfied = satisfied_course_ids(profile)
    kwargs = dict(term_id=term_id, excluded=set(profile.excluded_course_ids), failed=failed_course_ids(profile))
    eligibility = {cid: pre.evaluate(catalog, satisfied, cid, **kwargs) for cid in sorted(catalog.courses)}
    eligible_ids = [cid for cid, e in eligibility.items() if e.eligible]
    try:
        if RANKING_FAILURE in faults:
            raise ranking.RankingFailure("injected ranking failure")
        ranked = ranking.rank_courses(catalog, profile, satisfied, eligible_ids, normalized)
    except ranking.RankingFailure:
        ranked = None
    cohort = digest([catalog.catalog_version, ranking.ALGORITHM_VERSION, eligible_ids])
    return Evaluation(eligibility, ranked, normalized, satisfied, cohort)


def _issues(items: list[Issue]) -> list[dict]:
    return [i.as_dict() for i in items]


def _refs(reasons: list[ex.Reason]) -> list[dict]:
    seen, refs = set(), []
    for r in reasons:
        for ref in r.evidence_refs:
            if ref not in seen:
                seen.add(ref)
                refs.append({"source": ref[0], "record_id": ref[1]})
    return refs


def _component_dto(scored: ranking.ScoredCourse) -> dict:
    return {
        name: {"value": c.value, "weight": c.weight, "effective_weight": c.effective_weight,
               "contribution": c.contribution, "available": c.available}
        for name, c in scored.components.items()
    }


def _explain(reasons: list[ex.Reason], catalog: CatalogSnapshot, profile: StudentProfile,
             faults: frozenset[str], warnings: list[dict]) -> list[ex.Reason] | None:
    if EXPLANATION_FAILURE in faults:
        return None
    kept, dropped = ex.verify_evidence(reasons, catalog, profile)
    if dropped:
        warnings.append({"code": "EXPLANATION_EVIDENCE_MISMATCH", "message": f"Đã bỏ {len(dropped)} lý do không đối chiếu được bằng chứng."})
    return kept


def recommend(catalog: CatalogSnapshot, profile: StudentProfile, weights: Mapping[str, float] | None, *,
              request_id: str, term_id: str | None = None, include_ineligible: bool = True,
              faults: frozenset[str] = frozenset()) -> dict:
    warnings = _issues(validate_profile(profile, catalog))
    ev = evaluate(catalog, profile, weights, term_id, faults)
    degraded = False
    eligible_dtos: list[dict] = []
    explanation_missing = False

    if ev.ranked is None:
        degraded = True
        warnings.append({"code": "RANKING_UNAVAILABLE", "message": "Không tính được điểm xếp hạng; chỉ trả về danh sách đủ điều kiện, không có thứ hạng."})
        scored_list = [ranking.ScoredCourse(cid, None, {}) for cid, e in ev.eligibility.items() if e.eligible]
    else:
        scored_list = ev.ranked

    for scored in scored_list:
        course = catalog.courses[scored.course_id]
        elig = ev.eligibility[scored.course_id]
        item = {
            "course_id": course.course_id, "title": course.title, "credits": course.credits,
            "workload_hours_per_week": course.workload_hours_per_week,
            "rank": scored.rank, "score": scored.total, "score_percent": ranking.display_percent(scored.total),
            "unlocks": list(elig.unlocks),
        }
        if ev.ranked is not None:
            item["contributions"] = {n: c.contribution for n, c in scored.components.items() if c.available}
            item["components"] = _component_dto(scored)
            item["components_missing"] = scored.missing_components
            reasons = _explain(ex.explain_scored(catalog, profile, scored, elig), catalog, profile, faults, warnings)
        else:
            reasons = _explain(ex.explain_blocked(catalog, elig), catalog, profile, faults, warnings)
        if reasons is None:
            explanation_missing = True
            item.update(reason_codes=[], reasons=[], evidence_refs=[])
        else:
            item.update(reason_codes=[r.code for r in reasons], reasons=[r.as_dict() for r in reasons], evidence_refs=_refs(reasons))
        eligible_dtos.append(item)

    ineligible_dtos: list[dict] = []
    if include_ineligible:
        for cid, elig in ev.eligibility.items():
            if elig.eligible or pre.COMPLETED in elig.reason_codes or pre.EXCLUDED_BY_USER in elig.reason_codes:
                continue  # completed/excluded remain available through why-not
            course = catalog.courses[cid]
            item = {"course_id": cid, "title": course.title, "credits": course.credits,
                    "direct_missing_prerequisite_ids": list(elig.direct_missing_prerequisite_ids),
                    "transitive_missing_paths": [list(p) for p in elig.transitive_missing_paths],
                    "reason_codes": list(elig.reason_codes)}
            reasons = _explain(ex.explain_blocked(catalog, elig, term_id), catalog, profile, faults, warnings)
            if reasons is None:
                explanation_missing = True
                item.update(reasons=[], evidence_refs=[])
            else:
                item.update(reasons=[r.as_dict() for r in reasons], evidence_refs=_refs(reasons))
            ineligible_dtos.append(item)

    if explanation_missing:
        degraded = True
        warnings.append({"code": "EXPLANATION_UNAVAILABLE", "message": "Không tạo được lời giải thích; điểm và điều kiện tiên quyết vẫn được kiểm chứng."})
    status = "degraded" if degraded else ("ok" if eligible_dtos else "empty")
    return {
        "request_id": request_id, "contract_version": CONTRACT_VERSION, "catalog_version": catalog.catalog_version,
        "algorithm_version": ranking.ALGORITHM_VERSION, "normalization_policy": ranking.NORMALIZATION_POLICY,
        "weights": ev.weights, "term_id": term_id, "status": status,
        "comparable_candidate_set_id": ev.candidate_set_id,
        "eligible": eligible_dtos, "ineligible": ineligible_dtos, "warnings": warnings,
    }


def why_not(catalog: CatalogSnapshot, profile: StudentProfile, course_ids: list[str],
            weights: Mapping[str, float] | None, *, request_id: str) -> dict:
    unknown = [c for c in course_ids if c not in catalog.courses]
    if unknown:
        raise UnknownCourses(unknown)
    validate_profile(profile, catalog)
    ev = evaluate(catalog, profile, weights)
    by_id = {s.course_id: s for s in ev.ranked or []}
    ranked_with_score = [s for s in ev.ranked or [] if s.rank is not None]
    results = []
    for cid in dict.fromkeys(course_ids):
        elig = ev.eligibility[cid]
        item = {"course_id": cid, "eligible": elig.eligible,
                "direct_missing_prerequisite_ids": list(elig.direct_missing_prerequisite_ids),
                "transitive_missing_paths": [list(p) for p in elig.transitive_missing_paths]}
        if elig.eligible and cid in by_id:
            scored = by_id[cid]
            reasons = ex.explain_scored(catalog, profile, scored, elig)
            if scored.rank and scored.rank > 1 and ranked_with_score:
                reasons.insert(0, ex.explain_lower_rank(scored, ranked_with_score[0], len(ranked_with_score)))
            item.update(rank=scored.rank, score=scored.total, score_percent=ranking.display_percent(scored.total))
        else:
            reasons = ex.explain_blocked(catalog, elig)
        reasons, _ = ex.verify_evidence(reasons, catalog, profile)
        item.update(reason_codes=[r.code for r in reasons], reasons=[r.as_dict() for r in reasons], evidence_refs=_refs(reasons))
        results.append(item)
    return {"request_id": request_id, "contract_version": CONTRACT_VERSION, "catalog_version": catalog.catalog_version,
            "algorithm_version": ranking.ALGORITHM_VERSION, "results": results}


def _ranks_within(ranked: list[ranking.ScoredCourse], ids: set[str]) -> dict[str, int]:
    subset = [s for s in ranked if s.course_id in ids and s.total is not None]
    return {s.course_id: i for i, s in enumerate(sorted(subset, key=lambda s: (-s.total, s.course_id)), start=1)}


def _side(ev: Evaluation) -> dict:
    ranked = ev.ranked or []
    return {
        "weights": ev.weights,
        "eligible_course_ids": sorted(s.course_id for s in ranked),
        "scores": {s.course_id: s.total for s in ranked},
        "ranks": {s.course_id: s.rank for s in ranked},
        "comparable_candidate_set_id": ev.candidate_set_id,
    }


def simulate(catalog: CatalogSnapshot, profile: StudentProfile, weights: Mapping[str, float] | None,
             scenario: Scenario, *, baseline_version: str, request_id: str) -> dict:
    validate_profile(profile, catalog)
    baseline_digest = digest([profile, dict(weights or {})])
    baseline = evaluate(catalog, profile, weights)
    scenario_profile = apply_scenario(profile, catalog, scenario)
    try:
        validate_profile(scenario_profile, catalog)
    except ProfileInvalid as exc:
        first = exc.errors[0]
        raise InvalidScenario(first.field.replace("profile.", "scenario."), first.message) from exc
    try:
        scenario_eval = evaluate(catalog, scenario_profile, scenario.weights if scenario.weights is not None else weights)
    except ranking.InvalidWeights as exc:
        raise InvalidScenario("scenario.weights", str(exc)) from exc
    if digest([profile, dict(weights or {})]) != baseline_digest:  # defensive: baseline must be untouched
        raise RuntimeError("baseline mutated during simulation")

    before = set(_side(baseline)["eligible_course_ids"])
    after = set(_side(scenario_eval)["eligible_course_ids"])
    shared = before & after
    rb, ra = _ranks_within(baseline.ranked or [], shared), _ranks_within(scenario_eval.ranked or [], shared)
    sb = {s.course_id: s.total for s in baseline.ranked or []}
    sa = {s.course_id: s.total for s in scenario_eval.ranked or []}
    changes = [{"course_id": cid, "rank_before": rb.get(cid), "rank_after": ra.get(cid),
                "score_before": sb.get(cid), "score_after": sa.get(cid),
                "score_delta": (sa[cid] - sb[cid]) if sa.get(cid) is not None and sb.get(cid) is not None else None}
               for cid in sorted(shared, key=lambda c: (rb.get(c) or 10**6, c))]
    return {
        "request_id": request_id, "contract_version": CONTRACT_VERSION, "catalog_version": catalog.catalog_version,
        "algorithm_version": ranking.ALGORITHM_VERSION,
        "baseline_version": baseline_version, "baseline_digest": baseline_digest,
        "scenario_id": scenario.scenario_id, "scenario_version": scenario.scenario_version,
        "comparable_candidate_set_id": digest([catalog.catalog_version, ranking.ALGORITHM_VERSION, sorted(shared)]),
        "baseline": _side(baseline), "scenario": _side(scenario_eval),
        "changes": changes,
        "entered": sorted(after - before), "exited": sorted(before - after),
    }
