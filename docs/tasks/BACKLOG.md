# Backlog — AI-07 Explainable Course Recommender

Team: SE2026-T24 / SE.2026.14 · Cập nhật: 2026-10-06 · Contract: `0.1.0` (adopted)

Đề bài: *Gợi ý môn học từ mục tiêu và lịch sử giả lập, giải thích điều kiện tiên quyết và cho phép người dùng điều chỉnh ưu tiên.* Hạng mục bắt buộc: catalog, profile, ranking, prerequisite validation, explanation, what-if controls. Kiểm chứng bắt buộc: synthetic data, ranking tests, fairness checks, ADR rules vs ML.

**Quy ước:**
- **Owner** để trống thì thành viên tự điền tên khi nhận ticket. Mỗi ticket chỉ có một owner.
- **Trạng thái:** `TODO` → `DOING` → `REVIEW` → `DONE`.
- Ticket chỉ `DONE` khi test ở cột "Test" pass và có người khác owner review.
- Đường dẫn tuân theo cấu trúc bắt buộc: `docs/`, `src/backend`, `src/web`, `test/…`, `tools/`, `build/deploy`. Không tạo `backend/`, `frontend/`, `tests/` ở gốc repo.

Bằng chứng lượt chạy MVP backend: [runs/2026-10-06-mvp-backend/REPORT.md](runs/2026-10-06-mvp-backend/REPORT.md).

## Mốc 0 — Chốt quyết định (chặn mọi ticket code)

| ID | Việc | Kết quả | Owner | Trạng thái |
|---|---|---|---|---|
| T-00 | Nhóm họp chốt các mục NEEDS_INPUT trong `docs/tasks/ARCHITECTURE_HANDOFF.md`. Đề xuất: **dùng luôn policy fixture làm policy giả lập của dự án**: thang 0–10, qua môn ≥5, tiên quyết AND phải qua ở kỳ trước, trọng số mặc định .50/.20/.10/.20, API stateless | Ghi "ADOPTED 2026-xx-xx" vào `DECISIONS.md`, ADR-001 và FAIRNESS chuyển sang Accepted; đổi `contract_version` thành `0.1.0` | ĐinhTruong An | DONE (2026-10-06) |

## Lõi — bắt buộc theo đề

| ID | Việc | Đường dẫn chính | Prompt | Phụ thuộc | Tiêu chí nghiệm thu | Test | Owner | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| T-01 | Khung dự án: `pyproject.toml` (FastAPI, pytest), `package.json` web, lệnh chạy trong README | `src/backend/`, `src/web/`, `build/deploy/` | 07-build-release | T-00 | `pytest` và `npm test` chạy được, kể cả khi chưa có test; README có lệnh chạy | CI/local smoke | | REVIEW (MVP run 2026-10-06, chờ review độc lập) |
| T-02 | **Synthetic data**: catalog, goals, profiles và nhãn nhóm fairness | `tools/generate_synthetic_data.py` | features/01-catalog | — | Cùng seed thì output giống hệt; profile hợp lệ theo schema OpenAPI; 0 vi phạm tiên quyết; nhóm `has_failed` luôn có ≥1 môn rớt | `test/backend/test_synthetic_data.py` | | REVIEW (bản đầu đã có, 6 test pass) |
| T-03 | **Catalog**: model `Course`/`CatalogSnapshot`, adapter in-memory, kiểm tra ID trùng, tham chiếu treo, chu trình | `src/backend/domain/catalog.py`, `src/backend/data/` | features/01-catalog | T-01, T-02 | Snapshot lỗi thì bị từ chối, không trả eligibility | `test/backend/test_catalog.py` | | REVIEW (MVP run 2026-10-06, chờ review độc lập) |
| T-04 | **Profile**: validate lịch sử (không trùng trạng thái, grade khớp state, ID môn tồn tại) | `src/backend/domain/profile.py` | features/02-profile-goals | T-03 | `profile-valid.json` pass; `profile-invalid.json` bị 422 đúng trường | `test/backend/test_profile.py` | | REVIEW (MVP run 2026-10-06, chờ review độc lập) |
| T-05 | **Prerequisite validation**: eligibility, thiếu trực tiếp và đường bắc cầu | `src/backend/domain/prerequisites.py` | features/03-prerequisites | T-03, T-04 | Đúng oracle: BASE eligible `{ST201, SE201}`; AI301 thiếu ST201; FAILED không học được ST201; READY học được AI301, không học được DL401 | `test/backend/test_prerequisites.py` | | REVIEW (MVP run 2026-10-06, chờ review độc lập) |
| T-06 | **Ranking**: 4 thành phần, chuẩn hóa trọng số, tie-break theo `course_id` | `src/backend/domain/ranking.py` | features/04-ranking | T-05 | Oracle: trọng số `.8/.2` cho ST201 = .86, SE201 = .58; trọng số `.2/.8` cho .44/.82 (thứ hạng đảo); tổng đóng góp = total (sai số ≤1e-9); trọng số toàn 0, âm hoặc NaN bị 422 | `test/backend/test_ranking.py` (**ranking tests**) | | REVIEW (MVP run 2026-10-06, chờ review độc lập) |
| T-07 | **Explanation**: reason code + evidence; why-not | `src/backend/domain/explanations.py` | features/05-explanations | T-06 | Mọi lý do đều trỏ tới thành phần điểm hoặc bản ghi catalog có thật; môn bị chặn liệt kê đúng tiên quyết thiếu | `test/backend/test_explanations.py` | | REVIEW (MVP run 2026-10-06, chờ review độc lập) |
| T-08 | **What-if controls**: chạy lại với trọng số hoặc kịch bản mới, baseline bất biến | `src/backend/domain/simulation.py` | features/06-what-if | T-06, T-07 | Digest baseline không đổi; có `scenario_id` mới; rank delta chỉ tính trên môn có ở cả hai tập | `test/backend/test_simulation.py` | | REVIEW (MVP run 2026-10-06, chờ review độc lập) |
| T-09 | **API** `/v1`: catalog, profiles/validate, recommendations, why-not, simulations; map lỗi 400/409/422/503 | `src/backend/app.py`, `src/backend/routers/` | features/11-api-integration | T-05…T-08 | Response khớp OpenAPI; mọi fixture trong `contracts/examples` pass; catalog lỗi thì 503, không có ranking giả | `test/contract/`, `test/integration/` | | REVIEW (MVP run 2026-10-06, chờ review độc lập) |
| T-10 | **Web UI**: chọn mục tiêu, sở thích; xem gợi ý và lý do; thanh trượt trọng số (what-if); xem why-not | `src/web/` | features/10-web | T-01 (dùng fixture), sau đó T-09 | Chạy được với fixture mode (có nhãn rõ) và với API thật; hiển thị đủ 3 trạng thái normal/degraded/unavailable | `test/web/` | | TODO |
| T-11 | **Reliability**: tiêm lỗi catalog và ranking | `test/integration/` | features/12-reliability | T-09 | Theo bảng Q-01…Q-09 trong `RELIABILITY.md` | `test/integration/test_faults.py` | | TODO |

## Kiểm chứng — bắt buộc theo đề

| ID | Việc | Đường dẫn chính | Phụ thuộc | Tiêu chí nghiệm thu | Owner | Trạng thái |
|---|---|---|---|---|---|---|
| T-12 | **ADR rules vs ML**: review và chốt `docs/architecture/adr/ADR-001-rules-vs-ml.md` | `docs/architecture/adr/` | T-00 | ADR chuyển trạng thái Accepted; có ít nhất 2 người review và ghi tên | | REVIEW (bản nháp đã có) |
| T-13 | **Fairness checks** F-01…F-06 | `test/backend/test_fairness.py`, `tools/fairness_report.py` → `docs/tasks/evidence/fairness-report.md` | T-02, T-06, T-07 | F-01, F-02, F-05 pass; báo cáo F-03, F-04, F-06 có số liệu và seed | | TODO |
| T-14 | **Bằng chứng cho ADR**: chạy baseline ML nhỏ trên dữ liệu synthetic và so với rules | `tools/ml_baseline.py`, kết quả ghi vào mục Results của ADR-001 | T-02, T-06 | Có bảng 3 chỉ số theo mục "Evidence plan" của ADR; ghi rõ giới hạn của dữ liệu synthetic | | TODO |
| T-15 | **Kiểm chứng độc lập** toàn luồng + demo script | `docs/tasks/evidence/` | T-09, T-10, T-13 | Người không viết code chạy lại theo README thành công; có danh sách known limitations | | TODO |

## Stretch — ngoài đề, chỉ làm khi lõi đã DONE

| ID | Việc | Prompt | Ghi chú |
|---|---|---|---|
| S-01 | Semester plan theo trần tín chỉ (`POST /semester-plans`) | features/07-semester-plan | Đã có contract; không bắt buộc |
| S-02 | Roadmap nhiều kỳ (`POST /roadmaps`) | features/08-roadmap | Phụ thuộc S-01 |
| S-03 | Graph UI hiển thị cây tiên quyết | features/09-graph-ui | Cần `GET /catalog/graph` |
| S-04 | Container và deploy | 07-build-release | `build/deploy/` |

## Truy vết đề bài → ticket

| Yêu cầu đề | Ticket |
|---|---|
| Catalog | T-03 |
| Profile | T-04 |
| Ranking | T-06 |
| Prerequisite validation | T-05 |
| Explanation | T-07 |
| What-if controls | T-08, T-10 |
| Python/Node; rules + recommender; web UI | T-01, T-09, T-10 |
| Synthetic data | T-02 |
| Ranking tests | T-06 |
| Fairness checks | T-13 |
| ADR rules vs ML | T-12, T-14 |
