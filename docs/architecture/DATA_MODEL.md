# Data Model — Proposed Contract 0.1.0

Status: draft; no human acceptance recorded. Normative choices are marked PROPOSED in `DECISIONS.md`. IDs are stable case-sensitive strings; all records carry source/version provenance where relevant.

## Catalog

| Entity | Fields | Rules |
|---|---|---|
| `Course` | `course_id`, `title`, `description`, `credits`, `workload_hours_per_week?`, `career_goals[]`, `skills[]`, `mandatory_prerequisites[]`, `recommended_preparation[]`, `available_terms[]`, `catalog_version` | Credits positive integer; workload nonnegative decimal hours/week; mandatory and soft signals distinct |
| `CatalogSnapshot` | `catalog_version`, `as_of`, `courses[]`, `source`, `status` | immutable for a request; IDs unique; references resolve; DAG acyclic |
| `PrerequisiteEdge` | `prerequisite_course_id`, `dependent_course_id`, `kind=mandatory` | direction prerequisite → dependent |
| `SoftPreparation` | `course_id`, `signal_strength?`, `source_record_id` | never gates eligibility |

## Profile and state

`StudentProfile` is a synthetic, request-scoped object: `profile_id`, `history[]`, `career_goal_ids[]`, `interest_ids[]`, `workload_preference`, `max_credits_per_term`, `excluded_course_ids[]`, `contract_version`. `HistoryRecord` has `course_id`, `state` (`passed|failed|planned`), `grade?`, `completed_term?`, `source_record_id?`. Scenario-only `hypothetical_passed[]` is never written to baseline history. Proposed grade scale is 0–10; proposed passing threshold is >=5. Missing grade is unknown and cannot infer pass. A later accepted explicit pass status may exist without grade only if policy allows; unresolved. Duplicate/conflicting states are invalid. Planned courses do not satisfy prerequisites.

`WorkloadPreference` is `hours_per_week_budget` (nonnegative number, required for a workload score) plus optional `direction=lower|higher|neutral`; `B` is a preference budget, not a semester-credit cap. Lower direction favors less estimated workload up to B; higher favors more up to B; neutral rewards workload up to B and penalizes excess. Semester credits are integer credits, not workload hours. Missing course workload makes workload component unavailable; renormalize weights over available components and report `components_missing`, or reject if all are missing. User preference missing uses configured default budget only if that default is explicitly shown.

## Eligibility, scores, explanations

`EligibilityResult`: `eligible`, `direct_missing_prerequisite_ids[]`, `transitive_missing_paths[][]`, `conditional_unlocks[]`, `reason_codes[]`, `completed_exclusion`. Eligibility states `eligible|ineligible|invalid_catalog`; selection `unselected|selected`; plan inclusion `included|excluded_credit_limit|excluded_user|unscheduled_constraint` are independent.

Score components all normalized to `[0,1]`: `goal_match`, `interest_match`, `preparation`, `workload_fit`. `ScoreBreakdown` contains each component's value, `weight`, `contribution`, `available`, `evidence_refs[]`; `total` is in `[0,1]`, displayed as percent rounded to one decimal only after summing unrounded products. If missing components occur, divide weighted sum by sum of available weights; if no positive available weight return no score with `NO_SCORABLE_COMPONENTS`. Each response carries `algorithm_version` and `normalization_policy`.

`Explanation`: stable `reason_codes[]`, rendered deterministic `reasons[]`, component references, evidence references (`source`, `record_id`, `catalog_version`), warnings, missing prerequisites, conditional unlocks. Text is generated from actual evidence and contribution, not free-form claims.

## Plan and scenario

`PlanEntry`: `course_id`, `term_id`, `credits`, `eligibility_at_plan_time`, `selection_source`, `status`. `SemesterPlan`: requested course IDs, included IDs, unscheduled IDs with reasons, credit cap/used/remaining, `complete|partial|infeasible`; no silent removal. `Roadmap`: bounded `horizon_terms[]`, per-term plan, unmet requirements, `complete|partial|infeasible`; each prerequisite must be passed historically or scheduled in an earlier term. Availability comes from catalog; no availability means unknown, not “offered every term.”

`Scenario`: unique `scenario_id`, `baseline_version`, `scenario_version`, sparse changes to goal IDs, weights, workload preference, credit cap, exclusions/selections, and hypothetical completion. Baseline payload/results are immutable. Course ranks are compared only within same catalog version, algorithm version, eligibility cohort, and candidate set; report comparison-set ID and count. Entrants/exits are eligibility/candidate changes, not rank deltas.

## Proposed state transitions

- `planned` → `passed|failed` only from an explicit history update in a future persisted design; v0.1 operations are stateless and make no transition.
- Scenario `hypothetical_passed` affects scenario eligibility only and expires with that scenario.
- A pass record remains a pass even if synthetic prerequisite ancestors are absent; validation emits a history warning rather than rewriting it.
- Failed grade never satisfies a mandatory prerequisite. A failed course is not treated as passed; whether it may be recommended as a retake and how repeats/grade replacement work are unresolved and must be adopted before implementation.
