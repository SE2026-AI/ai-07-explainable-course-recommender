# Kiểm thử

## Môi trường

Tạo một môi trường ảo cho dự án, kích hoạt nó, rồi cài thư viện:

```bash
pip install -r requirements.txt
```

Cần Python 3.11 trở lên; CI chạy 3.11. Thư mục `.venv/` đã nằm trong `.gitignore`. Nếu một lệnh báo
`ModuleNotFoundError`, nguyên nhân thường là chưa kích hoạt môi trường ảo.

Kiểm thử cần một máy chủ PostgreSQL. Nhóm chạy nó bằng Docker:

```bash
docker compose -f build/deploy/docker-compose.yml up -d      # bật
docker compose -f build/deploy/docker-compose.yml down       # tắt, giữ dữ liệu
docker compose -f build/deploy/docker-compose.yml down -v    # tắt, xóa sạch dữ liệu
```

Cấu hình mặc định — PostgreSQL 16, cổng `5432`, tài khoản `coursereco`, database `course_recommender` —
khớp giá trị mặc định trong `src/data/db/build.py`, nên không cần khai biến môi trường nào.

Khi dùng cấu hình khác, khai `DATABASE_URL` dạng `postgresql+psycopg://user:pass@host:port/dbname`, hoặc
`TEST_DATABASE_URL` nếu muốn kiểm thử trên một máy chủ riêng. Tài khoản kết nối phải có quyền `CREATEDB`
(xem mục Database tạm).

## Chạy

```bash
pytest
pytest -q                                   # gọn
pytest test/test_reference_data.py          # một file
pytest -k tien_quyet                        # theo tên test
pytest --cov=src --cov-report=term-missing  # kèm độ phủ
```

Kiểm tra mã nguồn chạy riêng, cấu hình ở `pyproject.toml`. CI chạy lệnh này trước `pytest`:

```bash
ruff check .
```

Trước khi mở pull request, nếu có sửa lược đồ hoặc code sinh dữ liệu thì phải sinh lại các file dẫn xuất
và commit kèm — xem `tools/README.md`.

## Database tạm

Mỗi phiên test tự tạo một database tên `tmp_coursereco_<chuỗi ngẫu nhiên>` trên máy chủ đang trỏ tới, nạp
CSV vào đó, và xóa khi kết thúc. Bộ kiểm thử **không bao giờ** đọc hay ghi database làm việc, nên chạy
`pytest` không làm mất dữ liệu đang có. Đổi lại, tài khoản kết nối phải có quyền `CREATEDB`.

Nếu một phiên test bị ngắt giữa đường, database tạm có thể còn sót lại; xóa bằng
`DROP DATABASE "tmp_coursereco_…" WITH (FORCE);` hoặc dựng lại container.

Hai fixture dựng sẵn trong `conftest.py`:

| Fixture | Dữ liệu |
| --- | --- |
| `repo` | `data/seed` và `data/synthetic` — dữ liệu thật của dự án |
| `repo_all` | Thêm `test/fixtures/seed_demo` (trường giả lập) và `test/fixtures/students` (sinh viên kiểm thử) |

## Các file

| File | Kiểm |
| --- | --- |
| `test_smoke.py` | Gói `src` import được |
| `test_schema.py` | Lược đồ biên dịch được; các ràng buộc thật sự chặn dữ liệu sai |
| `test_reference_data.py` | Dữ liệu chương trình đào tạo đúng văn bản và tự nhất quán |
| `test_student_data.py` | Dữ liệu sinh viên hợp lệ theo quy chế |
| `test_fixtures.py` | Tầng truy cập dữ liệu trả đúng tình trạng học tập của sinh viên kiểm thử |
| `test_repository.py` | `Repository` trả đúng số liệu mà tầng nghiệp vụ và tầng API sẽ dùng |
| `test_rules_status.py` | Trạng thái học phần khớp toàn bộ `expected_course_status.csv` |
| `test_scoring.py` | Công thức sáu tiêu chí xếp hạng; **không cần database** |
| `test_selection.py` | Luật khối tự chọn khi chọn `k` môn; **không cần database** |
| `test_explain.py` | Câu chữ của trạng thái học phần và vi phạm kế hoạch; **không cần database** |
| `test_recommender_contract.py` | Hợp đồng của thuật toán gợi ý trên toàn bộ sinh viên |
| `test_api.py` | Tám endpoint API v1 và định dạng lỗi theo hợp đồng |

Các bài trong `test_reference_data.py` và `test_student_data.py` chạy cho **mọi** chương trình đào tạo có
trong dữ liệu, nên thêm một khung mới là tự động được kiểm.

## Dữ liệu kiểm thử

`fixtures/students/` chứa các sinh viên kiểm thử cố định và đáp án đi kèm, sinh ra bằng
`python -m tools.generate_fixtures`:

| File | Nội dung |
| --- | --- |
| `cases.csv` | Mô tả tình huống của từng sinh viên kiểm thử |
| `expected_course_status.csv` | Trạng thái đúng của từng học phần đối với từng sinh viên |
| `course_registrations.csv` | Các môn sẽ đăng ký nếu học đúng kế hoạch, dùng để đo độ chính xác của gợi ý |

`fixtures/seed_demo/` là một trường giả lập với thang điểm và khung riêng, dùng để bảo đảm hệ thống không
viết cứng mã trường, mã học phần hay ngưỡng điểm đạt nào.

Thêm một tình huống kiểm thử: thêm một phần tử vào `CASES` trong `tools/generate_fixtures.py` rồi chạy lại
script.
