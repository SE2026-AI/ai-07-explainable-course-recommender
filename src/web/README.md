# AI-07 Web

React + Vite + TypeScript. Thành phần *Web* của AI-07 (`src/web/`, ảnh chụp và ghi chú giao diện ở `docs/ui/`).

**Nguồn sự thật duy nhất của tầng gọi API là [`docs/api/openapi.json`](../../docs/api/openapi.json)**, đọc
cùng [`docs/architecture/api-contract.md`](../../docs/architecture/api-contract.md). Không lấy đường dẫn
hay kiểu dữ liệu từ đặc tả nào khác.

## Chạy

Trong `src/web/` (PowerShell dùng `npm.cmd` nếu `npm.ps1` bị chặn):

```sh
npm install
npm run dev        # http://localhost:5173
npm run lint
npm test
npm run build
```

### Biến môi trường

Đặt trong `src/web/.env.local` (xem `.env.example`).

| Biến | Giá trị | Ý nghĩa |
| --- | --- | --- |
| `VITE_API_MODE` | `mock` (mặc định) \| `live` | `mock` phát lại ví dụ JSON của hợp đồng, không cần backend. `live` gọi backend thật |
| `VITE_API_BASE_URL` | mặc định `/v1` | Gốc của API. Dev server proxy `/v1` về `http://127.0.0.1:8000` |

Chạy `live`: dựng database và chạy backend theo [`docs/setup.md`](../../docs/setup.md)
(`uvicorn src.api.main:app --port 8000` ở thư mục gốc repo), rồi `VITE_API_MODE=live npm run dev`.

## Tầng API (`src/api/`)

| File | Vai trò |
| --- | --- |
| `types.ts` | **Sinh tự động** bằng `npm run gen:api` từ `docs/api/openapi.json`. Không sửa tay |
| `schema.ts` | Tên gọn cho các kiểu trong `types.ts` (`Meta`, `CurriculumCourse`, …) |
| `client.ts` | `ApiClient`, `createLiveClient`, `createMockClient`, `createApiClient` (chọn theo `VITE_API_MODE`) |
| `errors.ts` | `ApiError` theo §5: `status`, `code`, `message`, `details`; `userMessage` là câu tiếng Việt cho người dùng |
| `mock.ts`, `mocks/` | Mock, ba kịch bản `success`, `empty`, `error` |

Khi `openapi.json` đổi (ví dụ thêm endpoint sinh viên), chạy `npm run gen:api` rồi thêm phương thức vào
`client.ts`. `npm run check:api` báo lỗi nếu `types.ts` đã cũ so với `openapi.json`.

Client hiện gọi 8 endpoint đang chạy: `/v1/health`, `/v1/meta`, `/v1/universities`, `.../terms`,
`.../curricula`, `.../curricula/{code}`, `.../curricula/{code}/courses`, `/v1/data-issues`.

### Lỗi

- Mọi lỗi từ API thành `ApiError`. `userMessage` map `code` sang câu tiếng Việt; mã chưa biết thì dùng
  `message` của server.
- `route_not_found`, `method_not_allowed`, `http_error` có `isRoutingError = true`: client gọi sai đường dẫn
  hoặc phương thức. Giao diện hiện chúng như lỗi lập trình, không phải lỗi dữ liệu của sinh viên.
- `validation_error`: `fieldErrors` đọc từ `details.fields`.
- Client tự đặt hai mã không bao giờ đến từ server: `network_error` (không kết nối được, `status = 0`) và
  `bad_response` (phản hồi không phải JSON hoặc lỗi không đúng định dạng §5).

### Mock

- `mocks/contract/`: **nguyên văn** các khối JSON của `api-contract.md` §5 và §6.1–6.8. Test
  `contract-fixtures.test.ts` đọc lại file hợp đồng và so từng khối, nên hợp đồng đổi mà mock không đổi thì
  test đỏ.
- `mocks/seed/`: hợp đồng không có ví dụ cho health, universities, terms, curricula. Bốn file này là phản hồi
  thật của backend trên `data/seed`.
- Mock phát lại cố định, không lọc theo mã trường hay mã khung được chọn.

## Quy ước

- §9.5: trường lạ trong phản hồi được bỏ qua, không làm vỡ client.
- §4.2: `prerequisite_groups` hiện đúng hai tầng, các nhóm nối bằng **và**, mã trong một nhóm nối bằng
  **hoặc** (`components/Prerequisites.tsx`). Không làm phẳng.
- `algorithm_version` từ `/v1/meta` luôn hiện ở đầu trang (§6.1).
- Không tính điểm, thứ hạng hay điều kiện tiên quyết ở client.
