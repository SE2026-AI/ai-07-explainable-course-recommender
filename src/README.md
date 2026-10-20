# Mã nguồn

Backend là một khối duy nhất, chia thành các gói độc lập. Gói nghiệp vụ không phụ thuộc vào web server,
nên test được từng gói mà không cần dựng API.

| Gói | Làm gì | Không làm gì |
| --- | --- | --- |
| `data/` | Đọc PostgreSQL, trả về pandas DataFrame. **Mọi câu SQL nằm ở đây** | Luật học vụ, xếp hạng |
| `rules/` | Trạng thái của từng học phần: tiên quyết, môn đang nợ, khối tự chọn | Xếp hạng, câu chữ |
| `recommender/` | Xếp hạng sáu tiêu chí trong số học phần mà `rules/` cho phép, chọn `k` môn | Quyết định môn nào được học |
| `explain/` | Dựng câu tiếng Việt từ dữ liệu mà các gói trên tính ra | Quyết định môn nào được gợi ý |
| `api/` | FastAPI: định tuyến, validate, dựng phản hồi theo hợp đồng | Tự tính lại trạng thái hay tự viết câu giải thích |
| `web/` | Giao diện tham khảo, gọi API qua HTTP như mọi client khác | Gọi thẳng vào mã Python |

Chiều phụ thuộc chỉ đi một hướng: `api` → `recommender` → `rules` → `data`; `explain` được `recommender`
và `api` gọi tới. `test/test_api.py` quét cây cú pháp để bảo đảm không có SQL nào nằm ngoài `data/`.

| Tài liệu | Nội dung |
| --- | --- |
| `docs/architecture/api-contract.md` | Hợp đồng API v1 |
| `docs/architecture/data-model.md` | Lược đồ dữ liệu và cách đọc qua `Repository` |
| `docs/architecture/ranking.md` | Công thức sáu tiêu chí xếp hạng |
