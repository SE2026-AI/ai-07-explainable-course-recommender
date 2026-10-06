# Nghiên cứu liên quan — AI-07 Explainable Course Recommender

Ngày nghiên cứu: 2026-10-04. Dự án: SE2026-T24 / SE.2026.14.
Phạm vi: course recommendation, prerequisite enforcement, scoring transparency, why/why-not explanations, what-if analysis, academic planning, career-skill alignment.

## Phương pháp và phạm vi xác minh

**Nguồn sử dụng:** trang sản phẩm chính thức, developer documentation, institutional repositories, arXiv, ACM DL, EDM/CEUR proceedings, và SciTePress/Springer/Elsevier metadata.

**Mức độ xác minh cho từng mục:**
- *Verified technical capability* — xác nhận qua tài liệu kỹ thuật chính thức hoặc full-text paper.
- *Marketing/vendor claim* — tuyên bố từ trang sản phẩm, chưa được đánh giá độc lập.
- *Abstract-only* — chỉ đọc abstract/metadata; chưa xác minh phương pháp và kết quả chi tiết.
- *Full-text reviewed* — đọc toàn bộ nội dung paper và trích xuất phương pháp/kết quả.

Thiếu bằng chứng công khai không chứng minh một tính năng không tồn tại. Tuyên bố marketing không phải kết quả đánh giá độc lập. Không có sản phẩm trả phí, demo riêng, hay source code nào được kiểm tra trực tiếp.

## Phân biệt thuật ngữ

| Thuật ngữ | Định nghĩa trong ngữ cảnh AI-07 |
|---|---|
| **Course** | Môn học trong catalog, có mã, tín chỉ, prerequisite. |
| **Section** | Lớp cụ thể của một course trong một học kỳ (giờ, phòng, giảng viên). AI-07 đề xuất course, không chọn section. |
| **Degree audit** | Kiểm tra transcript so với yêu cầu tốt nghiệp. AI-07 không thay thế audit chính thức. |
| **Recommendation** | Đề xuất course phù hợp với profile/goals, kèm score breakdown. |
| **Roadmap** | Kế hoạch đa học kỳ tôn trọng prerequisite order và credit limits. |
| **Mandatory prerequisite** | Điều kiện bắt buộc — không đạt thì không đủ eligibility. Hard rule trong AI-07. |
| **Recommended preparation** | Khuyến nghị chuẩn bị — ảnh hưởng score nhưng không block eligibility. Soft signal. |
| **Degree/major what-if** | Thay đổi chương trình học và tính lại audit/plan. Các sản phẩm thương mại hỗ trợ dạng này. |
| **Ranking-priority what-if** | Thay đổi weight/preference và xem score/rank delta. Tính năng phân biệt của AI-07. |

---

## 1. Sản phẩm liên quan

### P1. Stellic — Progress / Planner / Pathways / Explore

Nguồn: [stellic.com](https://www.stellic.com/) · [docs.stellic.com](https://docs.stellic.com/) · [stellic.com/platform](https://www.stellic.com/platform)

**Khả năng đã xác minh (tài liệu kỹ thuật):**
- Progress: degree audit engine xử lý sub-requirements, double-counting, course substitution.
- Planner: drag-and-drop multi-year plan; prerequisite DAG visualization; calendar schedule builder với conflict detection.
- Explore (ra mắt cuối 2025): transfer articulation engine cho credit mobility ([PR Newswire](https://www.prnewswire.com/news-releases/stellic-launches-explore-to-revolutionize-the-transfer-credit-process-in-higher-education-302306766.html)).
- Partner API (`partnerapi/v1`): REST JSON, Personal Access Token, endpoints cho student profiles, audit states, planned courses, catalog structures.

**Đánh giá theo tiêu chí AI-07:**

| Tiêu chí | Stellic | Ghi chú |
|---|---|---|
| Prerequisite checking | Visual warning trên plan canvas; SIS enforcement | Không có per-course eligibility API riêng |
| Why/why-not explanation | Requirement bucket fulfillment only | Không có score breakdown hay why-not diagnostics |
| What-if analysis | Degree/major/catalog change | Không hỗ trợ ranking-weight what-if |
| Scoring transparency | Không có | Template & bucket matching, không có scoring formula |
| Partner API | Có (REST, PAT-protected) | Schema chi tiết yêu cầu partner credentials |
| Career alignment | NACE competency badging | Không có algorithmic skill-gap recommendation |

**Suy luận thiết kế cho AI-07:** Tham khảo unified plan workspace với completed/planned/blocked states. Không copy enterprise advising scope hay transcript processing.

### P2. Ellucian — Degree Works / Smart Plan

Nguồn: [ellucian.com/solutions/ellucian-degree-works](https://www.ellucian.com/solutions/ellucian-degree-works) · [ellucian.com/solutions/ellucian-smart-plan](https://www.ellucian.com/solutions/ellucian-smart-plan) · [Blog](https://www.ellucian.com/blog/maximizing-your-degree-audit-smart-planning-and-credential-discovery)

**Khả năng đã xác minh:**
- Degree Works: audit engine dùng ngôn ngữ Scribe để mã hóa degree requirements, GPA thresholds, residency rules.
- Smart Plan: constraint-satisfaction heuristic tự động tạo multi-term plan dựa trên Scribe audit. Self-healing roadmap khi student fail/drop course.
- Registration enforcement qua Banner/Colleague SIS.
- Award module: credential discovery cho stackable certificates.

| Tiêu chí | Ellucian | Ghi chú |
|---|---|---|
| Prerequisite checking | Strict Scribe enforcement + registration blocking | Corequisite và repeat rules |
| Why/why-not explanation | Audit block fulfillment | Không có ranking factor breakdown |
| What-if analysis | Degree/major change + auto-replanning (time/cost projection) | Không hỗ trợ weight what-if |
| Scoring transparency | Không có | Proprietary constraint-satisfaction solver |
| Partner API | Private Ethos APIs; campus network restricted | Không public |
| Career alignment | Program-level credential discovery | Không có course-to-skill recommendation |

**Suy luận thiết kế:** Tham khảo self-healing roadmap (tự cập nhật plan khi có thay đổi). Phân biệt rõ: AI-07 simulate changes mà không mutate baseline — khác với Smart Plan tự động replan.

### P3. Civitas Learning — Student Impact Platform

Nguồn: [civitaslearning.com/platform](https://www.civitaslearning.com/platform/) · [Academic Planning](https://www.civitaslearning.com/student-success-software/academic-planning-student-scheduling/)

*Lưu ý: Civitas Learning là entity độc lập (Francisco Partners), không thuộc Anthology.*

**Khả năng đã xác minh:**
- Collaborative degree planning với drag-and-drop workspace.
- Conflict-free schedule generation tính đến student commitments (jobs, sports).
- Proactive roadblock detection: real-time alerts cho missing prerequisites, corequisites, term unavailability.
- Predictive persistence analytics: ML models đánh giá retention/graduation probability.
- Career Readiness Index: theo dõi career milestone progress.

| Tiêu chí | Civitas Learning | Ghi chú |
|---|---|---|
| Prerequisite checking | Real-time canvas alerts | Registration enforcement qua SIS |
| Why/why-not explanation | Risk factor explanations (at-risk students) | Không có course recommendation explanations |
| What-if analysis | Alternative program template exploration | Không hỗ trợ weight what-if |
| Scoring transparency | Proprietary persistence ML | Không có course scoring engine |
| Partner API | Enterprise data connectors (private) | Không public REST API |
| Career alignment | Career Readiness Index + pathway tracking | Metric-level, không per-course skill mapping |

**Suy luận thiết kế:** Tham khảo việc phân biệt course selection vs section enrollment. Planning feedback cần visible cho student. AI-07 defer SIS/registration integration.

### P4. CollegeSource — uAchieve / TES

Nguồn: [collegesource.com/products/uachieve](https://www.collegesource.com/products/uachieve/) · [TES](https://www.collegesource.com/products/tes/)

**Khả năng đã xác minh:**
- uAchieve: deterministic rules engine — sub-requirements, credit minimums, grade thresholds, residency rules, repeat exclusions.
- uAchieve Planner (formerly u.direct): multi-term planning verified against audit logic.
- TES: course catalog repository và transfer equivalency management.
- Prerequisite/corequisite trees enforced trong audit encoding.

| Tiêu chí | CollegeSource | Ghi chú |
|---|---|---|
| Prerequisite checking | Strict rule validation | Audit-level, không advisory |
| Why/why-not explanation | Boolean audit: Satisfied/In-Progress/Unfulfilled | Không rank, không explain |
| What-if analysis | Degree/program what-if (pioneering standard) | Không weight what-if |
| Scoring transparency | Không áp dụng | Pure rule-matching, không scoring |
| Partner API | SOAP web services cho TES; không REST cho uAchieve | Partial |
| Career alignment | Không có | Curricular catalog only |

**Suy luận thiết kế:** uAchieve là benchmark cho deterministic audit correctness. AI-07 eligibility engine nên đạt mức chính xác tương đương cho prerequisite validation, nhưng bổ sung thêm scoring/explanation layer.

### P5. EAB Navigate / Navigate360

Nguồn: [eab.com/technology/navigate-overview](https://eab.com/technology/navigate-overview/) · [Course Planning Agent](https://eab.com/technology/course-planning-agent/)

**Khả năng đã xác minh:**
- Course Planning Agent (CPA): automated term-by-term plan generation từ catalog rules.
- Collaborative advisor-student roadmap workspace.
- Predictive risk modeling: critical milestone courses, success markers.
- Major & Career Explorer: kết nối majors với career outcomes, earnings, job market.

| Tiêu chí | EAB Navigate | Ghi chú |
|---|---|---|
| Prerequisite checking | Sequence validation từ major templates | SIS enforcement |
| Why/why-not explanation | Template & milestone rationale | Không có score breakdown |
| What-if analysis | Major Explorer; audit what-if qua integrated engine | Không weight what-if |
| Scoring transparency | Proprietary CPA solver | Không expose formula |
| Partner API | Private enterprise APIs | NDA-protected |
| Career alignment | Deep labor market data integration | Program-level, không per-course |

**Suy luận thiết kế:** Tham khảo major-career exploration UI. AI-07 có thể map career goals → skill sets → courses, nhưng bắt đầu với curated synthetic mappings.

### P6. Jenzabar One — Degree Audit & Academic Planning

Nguồn: [jenzabar.com/product/jenzabar-one/student](https://jenzabar.com/product/jenzabar-one/student) · [Unity Platform](https://jenzabar.com/blog/jenzabar-unity-platform-higher-ed-integration)

**Khả năng đã xác minh:**
- Degree audit engine: transcript vs program requirements.
- Advising Requirement Codes (ARCs): prerequisite configuration bao gồm transfer equivalents và non-course milestones.
- Registration enforcement: hard blocks cho unmet prerequisites/corequisites.
- Jenzabar One API & Unity iPaaS: REST APIs cho student/course/enrollment data.

| Tiêu chí | Jenzabar | Ghi chú |
|---|---|---|
| Prerequisite checking | Strict ARC enforcement tại registration | Comprehensive |
| Why/why-not explanation | Requirement checklist status | Không ranking explanation |
| What-if analysis | Program/major simulation | Không weight what-if |
| Scoring transparency | Không áp dụng | ERP audit, không scoring |
| Partner API | REST APIs + Unity iPaaS | Institutional admin focus |
| Career alignment | Campus Marketplace (workforce credentials) | Không per-course |

### P7. Coursera — Personalized Learning Paths (tham khảo MOOC)

Nguồn: [coursera.org/enterprise/articles/personalized-learning-paths](https://www.coursera.org/enterprise/articles/personalized-learning-paths) (cập nhật 2026-09-03).

Mô tả: learning path alignment với interests, career objectives, skill gaps trong workforce learning context.

**Lưu ý phân biệt:** Coursera hoạt động trong MOOC/workforce domain — không có mandatory academic prerequisites, credit requirements, hay degree audit constraints như university setting. Kết quả từ Coursera không generalize sang university academic planning mà không có bằng chứng riêng. Tham khảo cho goal-to-skill framing, không cho eligibility logic.

---

## 2. Nghiên cứu liên quan

### Nhóm A: Prerequisite-aware recommendation

#### R1. Finding Paths for Explainable MOOC Recommendation: A Learner Perspective

Frej, J., Shah, N., Knezevic, M., Nazaretsky, T., & Kaser, T. (2024). LAK '24, pp. 1–17. Preprint: [arXiv:2312.10082](https://arxiv.org/abs/2312.10082).
**Mức độ review: full-text.**

**Phương pháp:** Xây dựng heterogeneous Knowledge Graph trên hai benchmark MOOC (COCO: 25,979 learners, 23,319 courses; XuetangX: 6,548 learners, 687 courses). Entity types: Learner, Course, Teacher, Category, Concept/Skill, School. Concept extraction dùng skillNER. Đề xuất UPGPR (Unrestricted Policy-Guided Path Reasoning) — RL agent duyệt multi-hop paths từ learner đến candidate course với binary reward, loại bỏ 1-hop shortcuts mà không cần hand-crafted path templates.

**Kết quả:** UPGPR đạt/vượt NeuMF và CFKG trên NDCG, Recall, HR. User study (N=12 PhD students): path-based explanations đạt trust score cao nhất (μ=4.00/5 vs CF μ=3.44). **Path length 4 là optimal** — length 6 bị đánh giá quá verbose, length 2 thiếu context.

**Code/data:** GitHub [epfl-ml4ed/courserec](https://github.com/epfl-ml4ed/courserec). Cần review license trước khi reuse.

**Overlap với AI-07:** Graph-based explanation approach. Tuy nhiên: prerequisite DAG của AI-07 đơn giản hơn KG multi-hop; AI-07 không cần RL architecture cho prerequisite explanations. Tham khảo: show evidence path connecting history → topics → recommended course; giới hạn explanation complexity (≤ 4 hops).

#### R2. Incorporating Recommended Course Prerequisites into Similarity-Based Course Recommender Systems

Breuer, T. & Ropke, R.C. (2026). CSEDU 2026, pp. 213–220. DOI: [10.5220/0014665100004021](https://doi.org/10.5220/0014665100004021). Institutional record: [TU Wien](https://repositum.tuwien.at/handle/20.500.12708/228422).
**Mức độ review: abstract/metadata.** Full-text bị paywall (SciTePress captcha + subscription). ResearchGate: closed access.

**Nội dung từ abstract:** Tích hợp recommended prerequisite fulfillment vào similarity-based recommendation và đánh giá usability/plausibility. Matrix factorization baseline được ưa thích hơn về accuracy, nhưng prerequisite-aware constraints được chấp nhận tích cực cho explainability.

**Phân biệt quan trọng:** Paper này xử lý *recommended preparation* (soft signal), không phải *mandatory prerequisite* (hard eligibility rule). Không justify chuyển mọi suggested prerequisite thành blocking condition.

**Overlap với AI-07:** Trực tiếp liên quan đến prerequisite scoring component. Tham khảo: compare baseline vs prerequisite-aware; đánh giá cả comprehension/plausibility, không chỉ rank quality. Cần đọc full-text để xác minh methodology.

#### R8. Prerequisite-Aware Course Ordering Towards Getting Relevant Job Opportunities

Dai, Y., Yoshikawa, M., & Sugiyama, K. (2021). *Expert Systems with Applications*, 183, 115233. DOI: [10.1016/j.eswa.2021.115233](https://doi.org/10.1016/j.eswa.2021.115233).
**Mức độ review: abstract + partial methodology** (Elsevier ScienceDirect).

**Phương pháp:** Trích xuất technical skills từ job postings, xây dựng prerequisite dependency graph liên kết concepts across courses, tối ưu hóa course ordering thỏa prerequisite constraints đồng thời maximize job-skill coverage.

**Kết quả:** Vượt heuristic và collaborative sequencers, tạo valid learning trajectories rút ngắn skill gap cho target roles.

**Overlap với AI-07:** Kết hợp cả prerequisite enforcement (hard DAG ordering) và career alignment (skill-gain attribution). Tham khảo: skill-gain attribution per course → dùng trong explanation. AI-07 bắt đầu với curated mapping, không live job posting extraction.

#### R9. Modeling and Leveraging Prerequisite Context in Recommendation

Hu, H., Pan, L., Ran, Y., & Kan, M.-Y. (2022). CARS@RecSys '22. [arXiv:2209.11471](https://arxiv.org/abs/2209.11471).
**Mức độ review: full-text** (arXiv).

**Phương pháp:** Prerequisite Driven Recommendation (PDR) framework. Prerequisite Knowledge Linking (PKL) xây concept prerequisite graphs (75,000+ concept pairs, 3 domains). Neural model PDRS jointly optimizes prerequisite validation + recommendation ranking.

**Kết quả:** Vượt baselines trung bình 7.41%, và tới 17.65% trong cold-start scenarios.

**Overlap với AI-07:** Score factorization thành prerequisite readiness + topical preference — tham khảo trực tiếp cho score breakdown design. Can explain "why not" dựa trên missing prerequisite concepts. Code/data: GitHub (WING-NUS), academic license.

### Nhóm B: Explainability và explanation quality

#### R4. Improving Course Recommendation Systems with Explainable AI: LLM-Based Frameworks and Evaluations

Li, J., Lyu, Q., Qiu, W., & Khong, A.W.H. (2025). EDM 2025, pp. 206–215. [Full PDF](https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.long-papers.221/2025.EDM.long-papers.221.pdf).
**Mức độ review: full-text** (10 trang).

**Phương pháp:** Two-stage decoupled framework:
1. *Recommendation:* BERT-based transformer — grade embeddings + LLM course embeddings + semester embeddings → softmax ranking.
2. *Explanation:* Gemini 1.5 Flash với 4-component meta-prompt (persona, student history, course descriptions, requirements). 4 model variants: persona vs cognitive verifier pattern; outcome-based vs content-based syllabus; có/không relevance theory.

**Dataset:** 2,795 engineering students (NTU Singapore). Evaluation: 6 representative profiles × top-5 recommendations × 4 variants = 120 explanations. Expert panel: 3 instructors, 6-point Likert trên clarity/effectiveness/relevance/specificity.

**Kết quả:** Model D (cognitive verifier + content-based + relevance theory) đạt cao nhất: Clarity 5.4, Effectiveness 5.0, Relevance 5.1, Specificity 5.2. Content-based syllabus data vượt outcome-based vì cung cấp concrete topics cho causal justification. Cross-cohort robustness ổn định (~5.0–5.2) across top/average/struggling students.

**Hạn chế:** Chỉ faculty evaluation (N=3), không student evaluation. Text-only, không interactive what-if.

**Overlap với AI-07:** Nếu thêm natural-language paraphrasing, cần đánh giá evidence faithfulness riêng biệt với fluency. AI-07 giữ structured reasons + deterministic fallback. Không dùng paper này justify mandatory LLM use.

#### R5. What if Interactive Explanation in a Scientific Literature Recommender System

Guesmi, M., Chatti, M.A., Ghorbani-Bavani, J., Joarder, S., Ain, Q.U., & Alatrash, R. (2022). CEUR-WS Vol-3222, paper 7, pp. 1–18. [Full PDF](https://ceur-ws.org/Vol-3222/paper7.pdf).
**Mức độ review: full-text** (18 trang).

**What-if mechanism (RIMA platform):**
- *Global what-if:* Interactive bar chart hiển thị semantic similarity scores. Dynamic slider điều chỉnh filtering threshold. Color-coded feedback: blue (retained), green (newly qualifying), red (omitted). Drill-down per-topic contribution breakdown.
- *Local what-if:* Per-item "WHAT-IF?" button. Interest weight sliders → real-time score update. Keyword modulation → inspect metadata influence.

**User study:** N=12 researchers/grad students. Mixed-methods: think-aloud + ResQue framework questionnaire + semi-structured interview. User control ranked highest. What-if được sử dụng chủ yếu khi recommendations unexpected — như repair mechanism.

**Hạn chế:** Domain là scientific literature, không phải academic courses. N=12 là small sample. Effect sizes không generalize sang student population.

**Overlap với AI-07:** Tham khảo trực tiếp cho ranking-priority what-if UI: slider-based weight adjustment, before/after visualization, color-coded rank changes. Không transfer effect sizes hay assume benefits generalize to students.

#### R11. Making Course Recommendation Explainable: A Knowledge Entity-Aware Model (KEAM)

Yang, T., Ren, B., Ma, B., et al. (2024). EDM 2024, pp. 658–663. [EDM 2024 proceedings](https://educationaldatamining.org/edm2024/proceedings/).
**Mức độ review: full-text** (EDM open proceedings).

**Phương pháp:** Autoencoder với latent neurons explicitly aligned với KG entities. Loại bỏ opaque latent factors bằng cách map representations → known syllabus concepts.

**Kết quả:** Accuracy competitive với black-box neural CF; cung cấp concept-grounded rationales.

**Overlap với AI-07:** Tham khảo cho intrinsic interpretability — score components nên map trực tiếp về observable factors. AI-07 đã thiết kế transparent normalized components; KEAM confirm viability of concept-level transparency.

### Nhóm C: Knowledge graph và sequential modeling

#### R6. Explainable Course Recommendation with Knowledge Graphs: A Comparative Audit

Afreen, N., Boratto, L., Fenu, G., Malloci, F.M., Marras, M., & Soccol, A. (2026). *Data Mining and Knowledge Discovery*, 40(6), Article 94. DOI: [10.1007/s10618-026-01261-4](https://doi.org/10.1007/s10618-026-01261-4).
**Mức độ review: abstract/metadata.** Full-text bị publisher paywall.

**Nội dung từ abstract:** Comparative audit across diverse KG paradigms (path-based GNNs, entity-aware embeddings, semantic meta-paths) trên academic course datasets. Phân tích trade-off giữa recommendation accuracy (utility) và explanation fidelity (beyond-utility metrics).

**Overlap với AI-07:** Guidelines cho path-based educational explainers. Concept/skill nodes enable counterfactual audits. Cần đọc full-text để xác minh evaluation methodology.

#### R12. On the Way to Explainable Course Recommendation: Enriching Graph-Based Modeling with Sequential Signals

Khan, M.A.Z., Luo, D., & Polyzou, A. (2026). ACM RecSys '26. DOI: [10.1145/3773078.3831826](https://doi.org/10.1145/3773078.3831826).
**Mức độ review: abstract/metadata** (ACM DL/ResearchGate).

**Nội dung:** Kết hợp heterogeneous graph representations với sequential learning signals. Model enrollment histories dạng chronological paths across course dependency graphs.

**Overlap với AI-07:** Sequential modeling ngăn premature recommendation bằng cách verify chronological prerequisite fulfillment. Trajectory-based explanations phù hợp cho roadmap feature. Cần full-text review.

### Nhóm D: Multi-semester planning và degree advising

#### R7. Degree Planning with PLAN-BERT: Multi-Semester Recommendation Using Future Courses of Interest

Shao, E., Guo, S., & Pardos, Z.A. (2021). AAAI 2021, 35(17), pp. 15411–15419. DOI: [10.1609/aaai.v35i17.17826](https://doi.org/10.1609/aaai.v35i17.17826). arXiv: [2103.01186](https://arxiv.org/abs/2103.01186).
**Mức độ review: full-text** (arXiv/AAAI open access).

**Phương pháp:** BERT transformer adapted (masked sequence training + bidirectional attention) conditioned on historical courses VÀ pre-specified future courses of interest. Hỗ trợ multi-semester trajectory prediction, không chỉ next-semester.

**Kết quả:** Vượt BiLSTM và UserKNN cho multi-semester completion prediction. Students đánh giá cao long-term path personalization.

**Overlap với AI-07:** Trực tiếp liên quan roadmap feature — seed với hypothetical target courses/capstones để synthesize intermediate plans. Bidirectional attention implicitly captures prerequisite dependencies. Code: GitHub (UC Berkeley), MIT License.

**Lưu ý:** AI-07 roadmap dùng deterministic constraint-based approach; PLAN-BERT là learning-based alternative. Có thể tham khảo evaluation metrics nhưng không adopt architecture mà không justify.

#### R10. SmartCourse: A Contextual AI-Powered Course Advising System

Mi, Y., Yu, Y., & Zhao, Y. (2025). arXiv preprint: [2507.22946](https://arxiv.org/abs/2507.22946).
**Mức độ review: full-text** (arXiv).

**Phương pháp:** End-to-end advising engine (Ollama/LLMs). Ingests transcript histories + curriculum rulebooks. Novel metrics: PlanScore (curriculum validity), PersonalScore (student interest fit), Lift, Recall.

**Overlap với AI-07:** Tham khảo evaluation metrics (PlanScore/PersonalScore decomposition). Prerequisite enforcement qua rule parsing trước LLM — align với AI-07 approach (eligibility before ranking). Interactive web interface (CLI/Gradio) cho what-if scenarios. Code: GitHub, Apache 2.0/MIT.

#### R13. A Recommender System Architecture for University Curriculum Advising

Ma, Z., Hahsler, M., & Moore, P. (2025). AAAI Spring Symposium 2025. [AAAI SSS-25](https://aaai.org/symposium-series/spring-2025/).
**Mức độ review: pre-print + proceedings.**

**Phương pháp:** Hybrid architecture: LLM goal-based agent + graph-theoretic curriculum solver. Formulates bulletin requirements thành algorithm-ready knowledge graph. LLM cho dialogue/persona profiling/explanation; graph solver cho constraint guarantees.

**Kết quả:** Eliminates prerequisite violations trên engineering curricula (SMU). Giảm human advising overhead.

**Overlap với AI-07:** Tham khảo separation of concerns: deterministic constraint checking (graph solver) vs natural language generation (LLM). What-if: "What if I double major?" / "What if I drop Course X?". AI-07 tương tự: canonical eligibility engine (deterministic) + optional LLM cho evaluated semantic needs.

### Nhóm E: Career-skill alignment

#### R3. Course Recommender Systems Need to Consider the Job Market

Frej, J., Dai, A., Montariol, S., Bosselut, A., & Kaser, T. (2024). [arXiv:2404.10876](https://arxiv.org/abs/2404.10876).
**Mức độ review: abstract/metadata.**

**Nội dung:** Course recommendation aligned với learner goals và labor-market skills. LLM skill extraction + RL alignment.

**Overlap với AI-07:** Version goal-to-skill mappings; bắt đầu curated synthetic mapping, labor-market ingestion là extension. Không claim labor-market alignment từ hand-written career tags.

---

## 3. Ma trận so sánh tổng hợp

### 3.1. Sản phẩm thương mại vs AI-07

| Tính năng | Stellic | Ellucian DW/SP | Civitas | CollegeSource | EAB Navigate | Jenzabar | **AI-07 (mục tiêu)** |
|---|---|---|---|---|---|---|---|
| Prerequisite enforcement | Visual warning | Strict Scribe + block | Real-time alert | Strict Boolean | Template sequence | Strict ARC | **Canonical eligibility engine trước ranking** |
| Why/why-not explanation | Requirement only | Audit block | Risk factors | Satisfied/Unfulfilled | Template milestone | Checklist | **Score breakdown + why-not diagnostics + evidence references** |
| What-if (degree) | ✓ | ✓ (auto-replan) | Template explore | ✓ (pioneering) | Major Explorer | ✓ | Planned extension |
| What-if (ranking weight) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ Core feature** |
| Scoring transparency | ✗ | ✗ | ✗ | N/A | ✗ | N/A | **✓ Normalized components, documented tie-breaking** |
| Public API | Gated REST | Private Ethos | Private | SOAP (TES) | Private | REST/iPaaS | **✓ Versioned OpenAPI REST** |
| Career alignment | Badge-level | Credential | Career Index | ✗ | Labor market | Marketplace | **Curated goal-to-skill mapping** |

**Nhận xét:** Không sản phẩm thương mại nào cung cấp cả ba: transparent course scoring + why-not diagnostics + interactive ranking-weight what-if. Đây là tổ hợp mà AI-07 hướng đến, không phải feature đơn lẻ.

### 3.2. Nghiên cứu vs AI-07

| Paper | Prerequisite | Explainability | What-if | Career | Deployment |
|---|---|---|---|---|---|
| R1 Frej (UPGPR) | KG relations | Multi-hop paths (trust μ=4.0) | ✗ | ✗ | MOOC benchmarks |
| R2 Breuer | Recommended (soft) | Plausibility study | ✗ | ✗ | University electives |
| R3 Frej (job market) | ✗ | ✗ | ✗ | LLM skill extraction | Perspective paper |
| R4 Li (EDM) | ✗ | LLM cognitive verifier (5.4 clarity) | ✗ | ✗ | NTU engineering |
| R5 Guesmi (RIMA) | ✗ | Interactive slider/bar chart | **Global + Local** | ✗ | Literature domain |
| R6 Afreen (KG audit) | DAG relations | Beyond-utility metrics | Counterfactual audit | Skill nodes | Educational KG |
| R7 Shao (PLAN-BERT) | Implicit sequential | Attention weights | **Target conditioning** | Moderate | UC Berkeley |
| R8 Dai (ESWA) | **Hard DAG ordering** | Skill attribution | ✗ | **Job posting extraction** | University curriculum |
| R9 Hu (PDR) | **PKL concept gates** | Readiness/preference split | ✗ | ✗ | 3 domains |
| R10 Mi (SmartCourse) | Rule pre-filter | PlanScore/PersonalScore | **Gradio interface** | ✗ | CS undergrad |
| R11 Yang (KEAM) | Concept-level | **Intrinsic KG-aligned neurons** | ✗ | ✗ | MOOC |
| R12 Khan (RecSys) | Chronological verify | Trajectory explanations | ✗ | ✗ | University |
| R13 Ma (AAAI SSS) | **Graph solver guarantee** | Decoupled verification | **Goal-based scenarios** | ✗ | SMU engineering |
| **AI-07** | **Hard AND prerequisites** | **Score breakdown + why-not + evidence** | **Weight sensitivity + hypothetical completion** | **Curated mapping** | **Synthetic university** |

---

## 4. Suy luận thiết kế từ nghiên cứu

Các đề xuất dưới đây là *inferences* từ nghiên cứu, không phải quyết định đã được phê duyệt. PM/PO owns scope decisions.

### 4.1. Eligibility engine

Canonical prerequisite checking trước ranking (align với [common-context.md](../tasks/prompts/common-context.md) hard rules). Prerequisites là AND, passed courses only. Phân biệt rõ mandatory prerequisite (block eligibility) vs recommended preparation (ảnh hưởng score, tham khảo R2).
- *Từ R9 (PDR):* factorize score thành prerequisite readiness + topical preference → dùng cho score breakdown.
- *Từ R13 (AAAI SSS):* deterministic graph solver cho constraint guarantee trước khi bất kỳ ML/LLM component nào can thiệp.

### 4.2. Ranking và scoring

Transparent normalized components với documented contributions, stable tie-breaking, và version metadata.
- *Từ R11 (KEAM):* mỗi score component nên map về observable/verifiable factor, không opaque latent.
- *Từ sản phẩm:* Không enterprise nào expose scoring formula → đây là differentiation opportunity, nhưng cần validation, không phải novelty claim.

### 4.3. Explanation API

Return reason codes, readable reasons, evidence references, missing prerequisites, conditional unlocks.
- *Từ R4 (EDM):* content-based syllabus data cho causal justification tốt hơn outcome-based. Nếu thêm NL paraphrasing → đánh giá faithfulness riêng biệt với fluency; giữ structured fallback.
- *Từ R1 (UPGPR):* giới hạn explanation path ≤ 4 hops (path length 4 optimal cho comprehension vs informativeness).
- *Từ R2:* đánh giá cả plausibility và comprehension, không chỉ ranking accuracy.

### 4.4. What-if

Immutable baseline; show score/rank/eligibility/plan deltas.
- *Từ R5 (RIMA):* slider-based weight adjustment, real-time color-coded feedback (retained/new/removed), per-factor drill-down. Áp dụng cho ranking-priority what-if.
- *Từ R7 (PLAN-BERT):* target conditioning (specify future courses → synthesize intermediate plan). Áp dụng cho roadmap what-if.
- *Từ R13:* hypothetical goal scenarios ("What if I drop X?" / "What if I add minor Y?"). Phân biệt rõ: degree what-if (re-audit) vs ranking what-if (re-score).

### 4.5. Roadmap

Multi-semester plan tôn trọng prerequisite order, credit limits, và availability assumptions.
- *Từ R7 (PLAN-BERT):* bidirectional conditioning cho multi-semester planning.
- *Từ Ellucian Smart Plan:* self-healing roadmap concept (plan tự cập nhật khi course fail/drop). AI-07 không auto-replan, nhưng what-if có thể simulate impact.
- *Từ R12:* sequential signals ngăn premature recommendation trong future semesters.

### 4.6. LLM integration

Bắt đầu rules/content matching. LLM chỉ cho evaluated semantic/language need.
- *Từ R4:* LLM explanation quality phụ thuộc prompt engineering (cognitive verifier + content-based + relevance theory). Nếu dùng, cần grounded inputs + output validation.
- *Từ R13:* decouple constraint checking (deterministic) từ NL generation (LLM).
- *Từ common-context.md:* LLM cannot decide eligibility, scores, or plans.

### 4.7. Career-skill alignment

Curated synthetic goal-to-skill-to-course mapping, với extension path cho labor market data.
- *Từ R3 và R8:* skill extraction từ job postings là viable nhưng cần maintained pipeline. AI-07 bắt đầu curated, không claim automated alignment.
- *Từ Coursera:* goal-to-skill framing hữu ích, nhưng MOOC/workforce context khác university prerequisites. Không generalize.

---

## 5. Kế hoạch đánh giá (informed by references)

### 5.1. Correctness (proposed checks, chưa thực hiện)

| Check | Tiêu chí | Tham khảo |
|---|---|---|
| Prerequisite violation | Zero hard-prerequisite violations trên curated acceptance dataset | uAchieve standard; R9 PDR gates |
| Score reconciliation | Component contributions tổng = final score | R11 KEAM intrinsic mapping |
| Reproducibility | Fixed input/version → identical ranking | common-context.md deterministic rule |
| Baseline immutability | What-if không mutate original profile/results | R5 RIMA design |
| Roadmap validity | Prerequisite order respected; credit limits honored | R7 PLAN-BERT evaluation; Ellucian Smart Plan |

### 5.2. Usefulness (proposed study, chưa thực hiện)

| Dimension | Method | Tham khảo |
|---|---|---|
| Explanation comprehension | Participants explain one recommendation và one rejection | R4 clarity/effectiveness metrics |
| What-if utility | Compare baseline-only vs slider interface; task completion + time | R5 ResQue framework |
| Plausibility | Rate logical justification of recommendations | R2 plausibility evaluation |
| Trust | Before/after trust measurement | R1 trust scoring (μ=4.0/5) |

**Constraints:** Report actual participant count. Synthetic data → không establish real academic/career impact. Small expert panels (R4 N=3, R1 N=12, R5 N=12) là precedent nhưng cũng là limitation.

---

## 6. Câu hỏi chưa giải quyết

1. **Full-text chưa đọc:** R2 (CSEDU 2026, paywalled), R6 (DMKD 2026, paywalled), R12 (RecSys 2026, ACM DL access). Cần đọc để xác minh methodology/evaluation trước khi adopt design inferences.

2. **License review chưa hoàn thành:** Code từ R1 ([epfl-ml4ed/courserec](https://github.com/epfl-ml4ed/courserec)), R7 (PLAN-BERT, MIT), R9 (WING-NUS), R10 (SmartCourse, Apache 2.0/MIT). Cần review chi tiết trước khi reuse bất kỳ component nào.

3. **Prerequisite semantics:** OR, waivers, concurrent enrollment chưa được scope (common-context.md line 14). Các papers R8 và R9 xử lý soft prerequisites — cần quyết định scope trước khi tham khảo approach.

4. **MOOC-to-university generalization:** R1, R3, R11 dùng MOOC datasets (COCO, XuetangX, MOOCCube). Kết quả quantitative không tự động áp dụng cho university prerequisites/credit systems.

5. **LLM evaluation:** R4 dùng Gemini 1.5 Flash; R10 dùng Ollama; R13 dùng LLM agent. AI-07 common-context yêu cầu evaluated semantic need, grounded inputs, output validation, deterministic fallback. Chưa có evidence rằng LLM cần thiết cho AI-07 prototype.

6. **User study design:** Chưa có participant recruitment plan. R4/R5/R1 precedent: 3–12 participants, expert or researcher population. Cần xác định target population (students? advisors? cả hai?) và ethical review.

7. **Sản phẩm enterprise features:** Nhiều tính năng (Smart Plan solver, CPA logic, Civitas ML models) là proprietary. Không so sánh algorithm-level được, chỉ so sánh feature-level từ public documentation.

---

## 7. Disclosure

**Công cụ sử dụng:** Antigravity agents với web search, URL content reading, file analysis. Không truy cập paid products, private demos, hay restricted documentation portals.

**Nguồn không truy cập được:**
- R2 full-text (SciTePress paywall + captcha)
- R6 full-text (Springer paywall)
- R12 full-text (ACM DL restricted access)
- Stellic `docs.stellic.com` authenticated endpoints
- Ellucian Customer Center technical manuals
- Civitas Learning model parameters
- EAB CPA internal logic (NDA-protected)
- Jenzabar MyJenzabar portal documentation

**Reproduction không thực hiện:** Không reproduce experiment nào từ các papers. Không chạy code từ repositories. Không benchmark sản phẩm. Tất cả design inferences là proposals từ public evidence.

**Source code/UI:** Không copy source code hay UI từ bất kỳ sản phẩm hay paper nào vào implementation.

**Numeric results:** Tất cả số liệu được trích dẫn từ papers gốc; không invent metrics hay kết quả mới.

---

*Cập nhật cuối: 2026-10-04. Các đề xuất thiết kế là inferences, không phải quyết định. PM/PO owns scope decisions.*
