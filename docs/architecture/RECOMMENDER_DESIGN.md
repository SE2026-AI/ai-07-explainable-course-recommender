# Recommender Design — Proposed Algorithm 0.1

Status: draft, not approved. Rule-based scoring is deterministic and reviewable; it is not a probability of success, GPA estimate or employment guarantee. Eligibility runs before ranking and cannot be overridden by a score.

## Components and normalization

Weights are nonnegative finite decimals, at least one positive, normalized to sum to 1. Inputs outside `[0,1]`, NaN/infinity, unknown component keys and all-zero weights are 422 errors. Default proposed weights: goal .50, interest .20, preparation .10, workload .20. Defaults are provisional; UI must disclose them and allow adjustment. Stable ordering: total descending (unrounded), then `course_id` ascending ordinal. Return display score rounded half-up to one decimal percent; contributions retain precision, with total equal to their sum before display rounding.

| Component | Input/calculation | Meaning | Missing data / direction |
|---|---|---|---|
| `goal_match` | course goal tags vs explicit goal-to-course mapping; weighted Jaccard, `[0,1]` | documented career-goal coverage | no mapping => unavailable, never infer from title; higher is preferred |
| `interest_match` | profile interest tags vs course topic tags; weighted Jaccard | stated interest overlap | missing profile/catalog tags => unavailable; higher preferred |
| `preparation` | normalized count/strength of completed recommended preparation signals, capped at 1 | readiness evidence, not mandatory eligibility | no soft signal data => unavailable; higher preferred |
| `workload_fit` | with weekly budget `B>0`, course estimate `h`: `lower`: `max(0, 1-h/B)`; `higher`: `min(1,h/B)`; `neutral`: `1` when `h<=B`, else `max(0,1-(h-B)/B)` | fit to explicit weekly workload preference | missing budget or course hours => unavailable; direction is explicit |

Goal mapping is a separate versioned catalog artifact maintained by a domain owner; this specification deliberately does not claim that a goal string automatically yields scores. The prompt fixture supplies component values as an arithmetic oracle only.

When some components are unavailable, `total = Σ(w_i*x_i)/Σ(w_available)` across available components; return original and effective weights and missing list. No available positive weight means score absent, not zero. Contributions use effective weights and reconcile to total. Whether normalization-over-available is acceptable to product owner remains open.

## Worked fixture arithmetic

Fixture values: ST201 `(goal=1.0, workload=.3)`; SE201 `(goal=.5, workload=.9)`. Other components omitted, so normalize the two supplied weights (which already sum to one).

| Course | Career setting `.8/.2` | Light-workload setting `.2/.8` |
|---|---:|---:|
| ST201 | `1.0*.8 + .3*.2 = .86` | `1.0*.2 + .3*.8 = .44` |
| SE201 | `.5*.8 + .9*.2 = .58` | `.5*.2 + .9*.8 = .82` |
| CS101 (illustrative third candidate) | `.6*.8 + .7*.2 = .62` | `.6*.2 + .7*.8 = .68` |

CS101 values are added solely to satisfy the three-course hand example; they are not the fixture oracle or extracted goal match. Ranking reverses ST201/SE201 across the two settings. This arithmetic does not specify real goal-to-component extraction.

## Pipeline and explainability

1. Validate catalog/profile/weights and versions.
2. Exclude completed courses from recommendable-now; retain why-not lookup.
3. Calculate hard eligibility using passed-before-term states.
4. Keep eligible and ineligible relevant candidates in separate result arrays.
5. Score/rank eligible only; compute why-not for ineligible and eligible-but-not-selected items.
6. For optional plan, apply user selection and credit cap as separate deterministic step.

Reason codes include `GOAL_MATCH`, `INTEREST_MATCH`, `PREPARATION_SIGNAL`, `WORKLOAD_FIT`, `MISSING_PREREQUISITE`, `TRANSITIVE_BLOCKED`, `COMPLETED`, `LOW_RELEVANCE`, `WORKLOAD_MISMATCH`, `LOWER_RANK`, `PLAN_EXCLUDED_USER`, `PLAN_CREDIT_LIMIT`, `CONDITIONALLY_UNLOCKABLE`. Each rendered reason references actual component/evidence. Why-not low relevance/workload/lower rank are comparative and include thresholds or comparison-set facts; no claim that a course is objectively bad. Plan credit-limit explanations include cap, already selected IDs and course credits.

What-if reruns same engine with scenario overlay and returns baseline/scenario score components, totals, eligibility changes, entry/exit sets, and rank deltas only for shared comparable candidates. Ranking cohort key = catalog version + algorithm version + eligibility status + candidate set digest. Scenario gets new ID/version; never mutate baseline. Deterministic templates only. Any future LLM may paraphrase supplied validated reason codes and evidence; timeout, schema validation and deterministic fallback required, and output may not alter eligibility, score, plan or facts.
