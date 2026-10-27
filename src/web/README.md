# AI-07 Frontend (T62–T64)

React + Vite + TypeScript, bốn route `/profile`, `/results`, `/course/:id`, `/explain`.

Chạy trong `src/web/` (PowerShell dùng `npm.cmd` nếu `npm.ps1` bị chặn):

```sh
npm install
npm run dev
npm run lint
npm run build
npm test
```

Mặc định `VITE_API_MODE=mock`. Đặt `VITE_API_MODE=live` trong `.env.local` để gọi API; `/v1` được dev server chuyển tới `http://127.0.0.1:8000`. Có thể đặt `VITE_API_BASE_URL` cho API khác. Server production cần fallback route về `index.html`.

Mock phát lại fixture cố định, không suy diễn điểm/điều kiện theo hồ sơ. Panel giải thích có fixture AI301; môn khác hiện thông báo chưa có dữ liệu. `createMockClient("empty" | "unavailable")` hỗ trợ kiểm thử rỗng/503. Các JSON `*.mock.json` yêu cầu trong spec được copy nguyên từ `_ref/contracts/examples/`; riêng catalog/graph là request examples. Response bổ sung lấy từ `_ref/web/src/api/mocks/base.json`, graph dựng từ quan hệ catalog mẫu. Metadata mục tiêu/sở thích là tùy chọn form cục bộ vì contract không có `/catalog/meta`.

UI tái dùng ProfilePage, ResultsPage, WhyNot, Icons, lib/profile và CSS trong `_ref/web/src`. Không dùng chức năng AI explain. Test nằm trong `src/test/`.

## Chênh lệch với API contract (cần TV1 chốt trong API_CONTRACT)
- Web gọi `GET /catalog/meta` (danh sách mục tiêu nghề, chủ đề sở thích, phiên bản catalog) để dựng form Profile. Endpoint này **chưa có** trong `openapi.yaml` → đề xuất bổ sung. Hiện chỉ chạy bằng mock `src/api/mocks/meta.mock.json`.
- Mock catalog có thêm `topics`, `goal_relevance` ngoài schema `CatalogCourse` (contract không cấm trường thừa). Cần chốt giữ hay bỏ.
