# WEB-1 — Tầng API client (issue #17)

Ghi chú việc đã làm cho phần WEB-1 của issue #17, nhánh `feat/web-api-client`.

## Đã làm

- **Sinh types từ hợp đồng.** `npm run gen:api` chạy `openapi-typescript` trên `docs/api/openapi.json`, ra
  `src/web/src/api/types.ts`. `npm run check:api` báo lỗi nếu file đã cũ. `src/api/schema.ts` chỉ đặt tên gọn
  cho các kiểu sinh ra, không khai báo tay kiểu phản hồi nào.
- **Client cho 8 endpoint đang chạy:** `/v1/health`, `/v1/meta`, `/v1/universities`, `.../terms`,
  `.../curricula`, `.../curricula/{code}`, `.../curricula/{code}/courses`, `/v1/data-issues`. Mã tự nhiên
  trong đường dẫn được mã hóa URL.
- **Lỗi theo §5.** `ApiError` có `status`, `code`, `message`, `details` (object, không có `request_id`).
  `userMessage` map đủ 11 mã của bảng §5 sang câu tiếng Việt, mã lạ thì dùng `message` của server.
  `route_not_found`, `method_not_allowed`, `http_error` có `isRoutingError` và hiện là "Lỗi lập trình", không
  hiện như lỗi dữ liệu sinh viên. `fieldErrors` đọc `details.fields` của `validation_error`. Client tự đặt
  `network_error` và `bad_response` khi không nhận được phản hồi đúng §5.
- **Mock.** `mocks/contract/` là nguyên văn các khối JSON của `api-contract.md` §5, §6.1–6.8 (gồm cả ví dụ
  profile, course-status, recommendations, plan-check để dùng cho WEB-2..4). Hợp đồng không có ví dụ cho
  health, universities, terms, curricula; `mocks/seed/` là phản hồi thật của backend trên `data/seed`. Ba kịch
  bản: `success`, `empty`, `error`.
- **`VITE_API_MODE=mock|live`**, dev server proxy `/v1` về `127.0.0.1:8000`.
- **Trang khung chương trình** (`/catalog`): chọn trường, chọn khung, hiện khối kiến thức và học phần.
  Tiên quyết hiện đúng hai tầng §4.2: nhóm nối bằng "và", mã trong nhóm nối bằng "hoặc", có ngoặc khi kết hợp.
  `algorithm_version` từ `/v1/meta` luôn hiện ở đầu trang (§6.1). Trang `/data-issues` (§6.8).
  Có trạng thái tải, rỗng, lỗi kèm nút thử lại.
- **README** `src/web/README.md`: cách chạy, biến môi trường, nguồn sự thật là `docs/api/openapi.json`.

## Kiểm tra

- `npm run build`, `npm run lint`, `npm test` xanh, 49 test:
  - `contract-fixtures.test.ts` đọc lại `api-contract.md`, so từng khối JSON với mock, và kiểm tra bảng §5
    có đúng 11 mã và mỗi mã có câu tiếng Việt.
  - `client.test.ts`: đường dẫn và parse đúng ví dụ cho cả 8 endpoint; trường lạ ở mọi tầng không làm vỡ (§9.5);
    lỗi §5, lỗi định tuyến, 422, phản hồi không phải JSON, mất mạng, hủy request; mock ba kịch bản.
  - `app.test.tsx`: trang hiện meta và học phần; chọn trường rồi khung; rỗng và lỗi có thông báo;
    `Prerequisites` hiện đúng VÀ/HOẶC.
- Chạy `live` với backend local (PostgreSQL 16, `python -m tools.build_db`, `uvicorn src.api.main:app`):
  đọc được `/v1/meta`, khung `HUS-7480113QTD-2022` ra đủ 65 học phần; mã trường sai hiện
  `university_not_found` thay vì trang trắng. Ảnh: `docs/ui/web-1-catalog-live.png`.

## Chưa làm

WEB-2, WEB-3, WEB-4 phụ thuộc API-1, API-2, API-3: `openapi.json` hiện chưa có profile, course-status,
recommendations, plan-check, prerequisite-graph. Issue yêu cầu không gõ tay types, nên các màn đó làm khi
issue API merge: chạy `npm run gen:api`, thêm phương thức vào `client.ts`, mock đã có sẵn trong `mocks/contract/`.

Không sửa file nào ngoài `src/web/` và `docs/ui/`.
