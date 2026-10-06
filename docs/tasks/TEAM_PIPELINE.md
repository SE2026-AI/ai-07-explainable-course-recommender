# Pipeline và phân công — AI-07

Team ID: SE2026-T24 · Tên nhóm: SE.2026.14.

## Vai trò của bốn người
| Người | Trách nhiệm | Bàn giao |
|---|---|---|
|    ĐinhTruong an | Chốt yêu cầu, điều phối agent, review code, tích hợp, quyết định release | Backlog, contract được chốt, bản chạy, evidence |
| Thành viên A | Dùng AI làm dữ liệu mẫu và kiểm tra các ví dụ tiên quyết | Catalog/profile fixtures, expected results, báo lỗi dữ liệu |
| Thành viên B | Dùng AI hỗ trợ tính điểm và thiết kế case what-if; kiểm tra độc lập | Bảng tính tay score, baseline/scenario fixtures, báo sai explanation |
| Thành viên C | Dùng AI hỗ trợ giao diện/tài liệu; kiểm tra hành trình người dùng và demo | Review màn hình, bước tái hiện lỗi, demo script, hướng dẫn chạy |

Các thành viên nhận ticket nhỏ và giải thích được đầu vào, đầu ra, một quy tắc, một failure case. Bạn chịu trách nhiệm phối hợp và nghiệm thu. Agent thực thi ticket; mỗi artefact vẫn có người chịu trách nhiệm.

## Pipeline hệ thống
Hồ sơ + mục tiêu + ưu tiên → kiểm tra input → catalog → bỏ môn đã hoàn thành → kiểm tra tiên quyết → tính điểm các môn hợp lệ → ranking → explanation → API → UI.

Môn thiếu điều kiện đi vào why-not. What-if chạy lại cùng engine trên bản sao baseline. Roadmap chỉ coi môn hoàn thành ở kỳ trước là điều kiện cho kỳ sau.

## Pipeline triển khai và prompt tương ứng
Danh sách ticket, tiêu chí nghiệm thu và owner nằm trong [BACKLOG.md](BACKLOG.md). Cột "Ticket" dưới đây trỏ tới đó.

| Mốc | Prompt | Ticket | Phụ thuộc | Người review |
|---|---|---|---|---|
| 0. Chốt vấn đề, scope và policy giả lập | management/01-product-backlog.md | T-00 | Đề tài và repo | Bạn |
| 1. Kiến trúc, contract, ADR rules vs ML | 01-architecture.md | T-12 | Scope | Bạn, A, B, C |
| 2. Tạo task có thể giao | management/02-task-dispatch.md | BACKLOG.md | Contract được chốt | Bạn |
| 3. Khung dự án + synthetic data | 07-build-release.md, features/01-catalog.md | T-01, T-02 | T-00 | Bạn, A |
| 4. Dữ liệu/hồ sơ | features/01-catalog.md, 02-profile-goals.md | T-03, T-04 | Schema | A |
| 5. Tiên quyết | features/03-prerequisites.md | T-05 | Catalog/profile interfaces | A |
| 6. Ranking và giải thích | features/04-ranking.md → 05-explanations.md | T-06, T-07 | Eligibility | B |
| 7. What-if | features/06-what-if.md | T-08 | Ranking | B |
| 8. Web và API | features/10-web.md, 11-api-integration.md | T-09, T-10 | Contract fixtures; rồi backend thật | Bạn, C |
| 9. Fairness + bằng chứng ADR | — (xem FAIRNESS.md, ADR-001) | T-13, T-14 | Synthetic data, ranking | B, A |
| 10. Reliability | features/12-reliability.md | T-11 | Luồng tích hợp | Bạn |
| 11. Kiểm chứng độc lập | 06-verification.md | T-15 | Bản tích hợp | A, B, C theo phạm vi |
| 12. Sửa lỗi và review | management/03-review-change.md | — | Findings | Bạn và owner |
| 13. Chuẩn bị bàn giao | 07-build-release.md, 08-evidence-audit.md | — | Checks liên quan đạt | Bạn |
| Stretch (chỉ khi lõi xong) | features/07-semester-plan.md, 08-roadmap.md, 09-graph-ui.md | S-01…S-03 | What-if, graph API | B, C |

Có thể làm web shell bằng fixtures song song với backend sau khi chốt contract. Chỉ chạy song song khi file allowlist không giao nhau. Backend API/router/app entrypoint có một owner là integration agent; feature agents chủ yếu viết domain services.

## Cấu trúc phải giữ
- docs/architecture/: kiến trúc, schema/API, quyết định và thuật toán.
- docs/tasks/: backlog, pipeline, ticket, prompt log, truy vết và review.
- src/backend/: application, routers, domain, data.
- src/web/: web client; src/prototype/ giữ bản tham khảo.
- test/: backend, web, contract, integration.
- build/deploy/: runtime, build, container và release.
- tools/: sinh dữ liệu, đánh giá và tiện ích.

Không tạo backend/, frontend/, tests/ ở root. Nếu cần .github/workflows/, ghi rõ ngoại lệ CI.

## Cách gửi prompt cho agent
Gửi common-context.md + prompt tính năng + assignment-template.md đã điền. Có thể dùng role prompt 02–05 cho ticket lớn, hoặc feature prompt cho ticket nhỏ; chọn một prompt nhiệm vụ chính mỗi lượt. Không giao cả hai phạm vi chồng nhau cho hai agent.

Orchestrator phải đọc index và chọn prompt tính năng theo ticket. Mọi specialist nhận cùng contract version. Nếu contract thay đổi, thông báo các consumer và cập nhật fixtures trước khi tích hợp.

## Nghiệm thu
1. Contract và quy tắc đã được bạn review.
2. Core flow chạy thật từ UI tới API; fixture mode được ghi rõ.
3. What-if giữ baseline; plan/roadmap không vi phạm tiên quyết/tín chỉ.
4. Independent checks đạt; known limitations được ghi; chạy từ README được.

Mỗi task lưu prompt thực tế, output trích đoạn, giữ/sửa/bác bỏ, lý do và kết quả lệnh đã chạy. File prompt soạn sẵn chưa phải bằng chứng đã sử dụng AI. Chưa có timeline cố định vì chưa biết deadline; mốc trên thể hiện thứ tự và điều kiện bàn giao.
