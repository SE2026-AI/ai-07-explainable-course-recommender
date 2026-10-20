# Quy ước làm việc trong repo

Đọc cùng `README.md` (sản phẩm), `src/README.md` (các gói và chiều phụ thuộc) và
`docs/architecture/api-contract.md` (hợp đồng API — nguồn sự thật cho mọi thứ client nhìn thấy).

## Ngôn ngữ

- Tên định danh — biến, hàm, lớp, file, tên test — viết **tiếng Anh**.
- Comment, docstring, và mọi câu dành cho người đọc (`text`, `message` của API) viết **tiếng Việt**.
- Tên test mô tả điều được khẳng định, ví dụ `test_zero_weight_removes_the_reason_instead_of_contributing_nothing`.
  Các test cũ đặt tên tiếng Việt không dấu (`test_tong_tin_chi_khop_van_ban`) giữ nguyên, không đổi tên hàng loạt.
- Commit theo Conventional Commits tiếng Anh, chỉ một dòng tiêu đề, một thay đổi logic mỗi commit:
  `feat(data): add repository readers for the API layer`.

## Kiểu

- Hàm công bố ra ngoài gói (tên không bắt đầu bằng `_`) có type hint cho tham số và giá trị trả về.
  Code cũ bổ sung dần khi sửa tới, không tách riêng một đợt chỉ để thêm type hint.

## Ranh giới các tầng

- SQL chỉ nằm trong `src/data/`; `test/test_api.py` kiểm điều này bằng cây cú pháp.
- `src/rules/` quyết định trạng thái học phần, `src/recommender/` chỉ xếp hạng trong số môn được phép,
  `src/explain/` chỉ dựng câu chữ, `src/api/` không tự tính lại những thứ đó.
- Mỗi thành phần có một người phụ trách. Cần sửa ở thành phần khác thì mở issue cho người đó.

## Trước khi mở pull request

- `ruff check .` sạch (cấu hình ở `pyproject.toml`) và `pytest` xanh. Test cần PostgreSQL, xem `test/README.md`.
- Sửa lược đồ hoặc code sinh dữ liệu: sinh lại file dẫn xuất và commit kèm, xem `tools/README.md`.
- Sửa `src/api/`: chạy `python -m tools.export_openapi` rồi commit `docs/api/openapi.json`.
- Đổi cách tính điểm hoặc câu chữ của lời giải thích: tăng `ALGORITHM_VERSION`, xem `docs/architecture/ranking.md` mục 7.
