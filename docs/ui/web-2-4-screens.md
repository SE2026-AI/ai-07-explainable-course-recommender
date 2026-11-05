# WEB-2..4 — Màn hình sinh viên (issue #17)

Ghi chú việc đã làm cho WEB-2, WEB-3, WEB-4 của issue #17, nhánh `feat/web-student-screens`. Làm sau khi
`docs/api/openapi.json` có đủ 14 endpoint và hợp đồng cập nhật ngày 24/10 (`algorithm_version` 1.0.1,
`max_credits_per_term` 40, mã lỗi `service_unavailable`).

## Đồng bộ lại với hợp đồng mới

- Chạy lại `npm run gen:api`: `types.ts` có đủ 14 endpoint. Không khai báo tay kiểu phản hồi nào.
- Trích lại nguyên văn các khối JSON của `api-contract.md` vào `mocks/contract/`, thêm ví dụ §6.9
  (`prerequisite-graph.json`). Test `contract-fixtures.test.ts` kiểm tra cả khối mới.
- Thêm mã `service_unavailable` (503) vào bảng lỗi và câu tiếng Việt cho nó.
- Client có thêm `profile`, `courseStatus`, `recommendations` (GET), `recommend` (POST), `planCheck`,
  `prerequisiteGraph`.

## Màn hình

Route: `/students` chọn trường và nhập mã sinh viên, không có đăng nhập giả. Sau đó
`/students/:uni/:student/{profile,status,recommendations,plan,graph}`, có ô chọn học kỳ (`?term=`).

| Màn | Endpoint | Ảnh |
| --- | --- | --- |
| Hồ sơ (WEB-2) | §6.4 profile | [web-2-4-profile.png](web-2-4-profile.png) |
| Trạng thái học phần (WEB-2) | §6.5 course-status | [web-2-4-status.png](web-2-4-status.png) |
| Gợi ý (WEB-3) | §6.6 recommendations GET/POST | [web-2-4-recs.png](web-2-4-recs.png), [web-2-4-whatif.png](web-2-4-whatif.png) |
| Kế hoạch học kỳ (WEB-4) | §6.7 plan-check | [web-2-4-plan.png](web-2-4-plan.png), [web-2-4-plan-violations.png](web-2-4-plan-violations.png) |
| Sơ đồ tiên quyết (WEB-4) | §6.9 prerequisite-graph | [web-2-4-graph.png](web-2-4-graph.png) |

Ảnh chụp với backend thật (`VITE_API_MODE=live`) trên `data/seed`, sinh viên `HUS/24000041` và `HUS/26000032`.

## Lựa chọn trình bày

- **Hồ sơ.** GPA `null` hiện "Chưa có điểm", không hiện 0. Tên khối và tên môn lấy từ endpoint khung chương
  trình. Không hiện `fairness_group`, `gender` kể cả khi phản hồi lỡ chứa (có test).
- **Trạng thái.** Nhóm theo `status`, số đếm lấy từ `summary` của server. Mỗi dòng hiện câu `text` của
  server, tiên quyết còn thiếu hiện đúng hai tầng VÀ/HOẶC (§4.2). Trạng thái lạ vẫn hiện với mã gốc.
- **Gợi ý.** Giữ đúng thứ tự server. Lý do hiện động, chỉ những lý do có trong phản hồi (§4.4), không có ô
  cố định 6 tiêu chí. Cạnh `score` hiện "= tổng đóng góp X"; nếu lệch thì cảnh báo ⚠ (§7), client không tự
  tính lại thứ hạng. Sáu thanh trọng số khởi tạo từ `weights` của server; chỉnh trọng số, giả định
  (assumptions), bỏ qua (skip) hoặc đổi môn (swap) thì gửi POST. `what_if = true` thì hiện băng "kịch bản
  giả định". "Vì sao chưa…" lấy từ `not_eligible` của cùng phản hồi. Lỗi 422 liệt kê trường sai từ
  `details.fields`.
- **Kế hoạch.** Lưu trong `localStorage` theo trường và mã sinh viên. Mỗi lần đổi kế hoạch gọi lại
  plan-check. Hiện đủ mọi vi phạm, kể cả nhiều vi phạm trên một môn và vi phạm không gắn môn (ví dụ
  `credit_limit_exceeded`). Có ghi chú §6.7: môn trong cùng kế hoạch không được tính là đã đạt.
- **Sơ đồ.** Chỉ dựng từ `nodes`/`edges` của §6.9, không dựng từ dữ liệu khung. Cột theo
  `recommended_semester`. Nhóm một môn là cạnh liền (VÀ); nhiều môn cùng `group_no` là các cạnh đứt nối vào
  một nút tròn HOẶC rồi một cạnh liền tới môn đích. Màu nút theo course-status của sinh viên; môn mở khóa từ
  3 môn trở lên (lấy từ lý do `unlocks` của server) có dấu ★. Có lọc theo khối, phóng to/thu nhỏ, kéo, bấm
  vào nút để làm nổi môn đó và các môn liên quan.
  Dữ liệu seed hiện chưa có nhóm HOẶC nào trong sơ đồ, nên phần HOẶC được kiểm bằng test với dữ liệu tự dựng.

## Kiểm tra

- `npm run lint`, `npm test` (70 test), `npm run build`, `npm run check:api` đều qua.
- Chạy live với backend: đổi trọng số làm đổi thứ hạng; giả định "MAT2505 đạt, điểm 6" làm MAT1202 vào danh
  sách gợi ý và hiện băng giả định; `limit` 25 hiện lỗi 422 đúng trường; kế hoạch 16 môn ra 11 vi phạm,
  58/40 tín chỉ; mã sinh viên không tồn tại hiện thông báo `student_not_found`.
- Test web và `check:api` chưa chạy trong CI.
