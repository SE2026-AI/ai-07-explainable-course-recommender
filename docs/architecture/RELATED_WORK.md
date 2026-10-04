# Related Work and Product Research — AI-07

Research date: 2026-10-04. Project: SE2026-T24 / SE.2026.14. Scope: course recommendations, prerequisites, explanations, academic planning, and what-if.

Method: primary vendor pages/documentation and original research records/papers. Vendor capabilities are vendor descriptions, not independently benchmarked findings. Paper abstracts establish research scope, not reproducibility. No paid product, private demo, or source implementation was inspected. Full-text fetching of the EDM and CEUR PDFs later timed out; these two entries remain preliminary.

## 1. Relevant products

### P1. Stellic — Progress / Planner / Pathways
Source: [Stellic official product page](https://www.stellic.com/).
Observed: Planner lets students choose and modify planned courses; Pathways shows possible degree paths/timelines; Degree Audit shows progress toward degree requirements.
Relevance: high for catalog/profile/planning and visualization. This page does not establish user-adjustable score weights or per-course numerical breakdowns.
Design inference for AI-07: put recommendation, rationale and plan together, with completed/planned/blocked states. Do not copy enterprise advising and transcript processing scope.

### P2. Stellic Partner API
Source: [Official developer documentation](https://docs.stellic.com/).
Observed: REST JSON API at partnerapi/v1; protected access, status codes, pagination and integration/synchronization documentation. Catalog/student/plan-related resources are described.
Design inference: version our API, separate catalog and enrollment state, specify schemas/errors and fixture responses. Do not copy vendor credentials or claim our API is compatible with theirs.

### P3. Ellucian — Degree Works / Smart Plan / Award
Source: [Official explanation of degree audit, Smart Plan and Award](https://www.ellucian.com/blog/maximizing-your-degree-audit-smart-planning-and-credential-discovery).
Observed: Degree Works provides audit information; Smart Plan uses that information to build/update plans; the described product family supports what-if analysis around goals/credentials.
Relevance: high for academic roadmap and planning changes. Degree/credential what-if differs from changing ranking weights.
Design inference: simulate changes without mutating baseline; explain plan changes. Do not claim our heuristic is optimal or covers full graduation certification.

### P4. Civitas Learning — Academic Planning and Student Scheduling
Source: [Official platform page](https://civitaslearning.com/platform/).
Observed: platform includes collaborative degree planning, a class schedule builder, registration and student-facing guidance/mobile capabilities.
Relevance: high for the connection between student profile, plan and usable workflow. The page does not disclose a scoring algorithm equivalent to AI-07.
Design inference: distinguish choosing a course from enrolling in a section. Keep planning feedback visible. Defer registration/SIS integration.

### P5. Coursera — personalized learning paths (adjacent reference)
Source: [Official Coursera article](https://www.coursera.org/enterprise/articles/personalized-learning-paths), updated September 3, 2026.
Observed: describes aligning learning paths with interests, career objectives and skill gaps in workforce learning.
Relevance: medium; useful for goal-to-skill framing, different from university prerequisites and credit requirements. This article is not proof of a specific recommendation API or adjustable-weight UI.
Design inference: explicitly map career goals to course topics/skills and show supporting evidence. Do not imply guaranteed employment from course completion.

## 2. Research topics and papers

### R1. Finding Paths for Explainable MOOC Recommendation: A Learner Perspective
Authors: Jibril Frej, Neel Shah, Marta Knezevic, Tanya Nazaretsky, Tanja Kaser. arXiv submission: 2023.
Source: [Original research record and abstract](https://arxiv.org/abs/2312.10082).
Observed: graph reasoning produces explainable MOOC recommendations as paths; abstract reports a user study and experiments on COCO/Xuetang.
Design inference: show an evidence path connecting history, topics, goals and recommended course. A prerequisite DAG is not equivalent to the paper's richer knowledge graph. We do not need its reinforcement-learning architecture to implement prerequisite explanations.
Evidence depth: abstract/metadata reviewed; detailed experiments and implementation not reproduced.

### R2. Incorporating Recommended Course Prerequisites into Similarity-Based Course Recommender Systems for Higher Education
Authors: Tom Breuer, Rene Christian Ropke. CSEDU 2026, pages 213–220. DOI: 10.5220/0014665100004021.
Source: [TU Wien institutional record](https://repositum.tuwien.at/handle/20.500.12708/228422).
Observed: integrates recommended prerequisite fulfillment into similarity-based recommendation and evaluates usability/plausibility. The abstract says matrix factorization was generally preferred, while integration of prerequisites was accepted.
Design inference: compare a baseline with prerequisite-aware suggestions; evaluate comprehension and plausibility as well as rank quality. Important distinction: recommended preparation is a soft signal; mandatory prerequisite is a hard eligibility rule. The paper does not justify converting every suggested prerequisite into a blocking condition.
Evidence depth: institutional abstract/metadata, not full implementation.

### R3. Course Recommender Systems Need to Consider the Job Market
Authors: Jibril Frej, Anna Dai, Syrielle Montariol, Antoine Bosselut, Tanja Kaser. 2024 perspective paper.
Source: [Original paper record](https://arxiv.org/abs/2404.10876).
Observed: discusses course recommendation aligned with learner goals and labor-market skills; includes an initial approach using LLM skill extraction and RL alignment.
Design inference: version goal-to-skill mappings; begin with a curated synthetic mapping, with labor-market ingestion as an extension. We cannot claim labor-market alignment from hand-written career tags alone.
Evidence depth: abstract/metadata; no reported numeric results reused.

### R4. Improving Course Recommendation Systems with Explainable AI: LLM-Based Frameworks and Evaluations
Source: [EDM 2025 proceedings paper](https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.long-papers.221/2025.EDM.long-papers.221.pdf).
Preliminary observation: retrieved proceedings text describes explanation generation and prompt patterns grounded in prior-course knowledge. Full-text follow-up timed out.
Design inference: if natural-language paraphrasing is added, evaluate evidence faithfulness separately from fluency; preserve structured reasons and fallback. Do not make this source a justification for mandatory LLM use or claim verified experimental benefits.
Evidence depth: preliminary extracted text; full methods/results need further reading.

### R5. What if Interactive Explanation in a Scientific Literature Recommender System
Source: [Original CEUR workshop paper](https://ceur-ws.org/Vol-3222/paper7.pdf), 2022.
Preliminary observation: studies interactive what-if explanation in a literature recommender, rather than academic courses. Full-text follow-up timed out.
Design inference: treat changing priorities as an explanation mechanism, showing which factors and ranks changed. Do not transfer effect sizes or assume benefits generalize to students.
Evidence depth: preliminary extracted text; further methods/results review required.

## 3. Comparison with AI-07

| Reference | Main overlap | Useful adaptation | Unverified / out of scope |
|---|---|---|---|
| Stellic | academic plan, profile/progress | unified plan workspace and clear course states | custom scoring/explanation algorithm |
| Stellic API | partner integrations | versioned contracts, documented errors | vendor compatibility |
| Ellucian | audit, roadmap, what-if | compare baseline vs changed plan | optimal planning / official degree audit |
| Civitas | planning and scheduling workflow | distinguish course from section/enrollment | SIS registration |
| Coursera | goals and skill gaps | goal-to-skill evidence | university eligibility semantics |
| R1 | graph-based explanation | explicit explanation/dependency paths | adopting full KG/RL system |
| R2 | prerequisite-aware recommendation | separate preparation signals from hard prerequisites | general superiority of prerequisite scoring |
| R3 | career alignment | curated goal/skill mapping and extension path | real job-market prediction |
| R4/R5 | language/interactive explanations | evaluation questions and UI concepts | unreviewed experimental claims |

A blank or unverified capability is not evidence that a vendor lacks it. Public pages cannot establish a complete competitive feature matrix.

## 4. Proposed architecture/design decisions (inferences)

1. Canonical eligibility engine before ranking; distinguish required prerequisites from suggested preparation.
2. Ranking uses transparent normalized components with contributions, stable ties and version metadata.
3. Explanation API returns reason codes, evidence references and missing prerequisites.
4. What-if keeps baseline immutable and shows score/rank/eligibility/plan deltas.
5. Roadmap respects previous-semester completion and declares availability assumptions.
6. Start rules/content matching; add LLM only for an evaluated semantic/language need.
7. Treat product differentiation as a proposal: a compact, inspectable combination of why/why-not, adjustable weights and before/after planning on synthetic data. This is not a novelty claim.

## 5. Evaluation plan informed by references

Correctness: zero hard-prerequisite violations in the curated acceptance dataset; contribution totals reconcile; fixed input/version reproduces ranking; baseline unchanged; roadmap respects credits/order. These are proposed checks, not achieved results.

Usefulness: compare transparent baseline with a what-if interface; ask participants to explain one recommendation and one rejection. Measure task completion, explanation comprehension, time and perceived plausibility. Report actual participant count and study limitations. Synthetic offline data cannot establish real academic or career impact.

Next research steps: read full R1/R2 methods; inspect available code/data and licenses before reuse; complete R4/R5 full-text review; validate our proposed workflow with students/advisors. No external artefact has been copied into implementation.

## 6. Research/AI disclosure
User request: “reseach và tham khảo các đề tài hay công ty có sản phẩm liên quan”. Tool: Codex with web search/open. Evidence is the linked public sources; adaptation suggestions are explicitly marked as inferences. Product access and paper implementation reproduction were not performed.
