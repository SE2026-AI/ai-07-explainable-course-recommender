# Kiến trúc

| Tài liệu | Nội dung |
| --- | --- |
| `api-contract.md` | Hợp đồng API v1 giữa backend và các ứng dụng web, di động |
| `data-model.md` | Lược đồ dữ liệu, khóa nghiệp vụ, quy ước đặt tên, cách đọc qua `Repository` |
| `ranking.md` | Công thức sáu tiêu chí xếp hạng và cách dựng lời giải thích |

Tổng quan hệ thống, phạm vi và lộ trình: `README.md` ở thư mục gốc.

---

## Quyết định kỹ thuật

Những lựa chọn dưới đây không suy ra được từ việc đọc mã nguồn, nên được ghi lại cùng lý do.

### PostgreSQL cho mọi môi trường

Lược đồ dùng `JSONB` để lưu lời giải thích của mỗi lượt gợi ý, `TIMESTAMPTZ`, và chỉ mục duy nhất có điều
kiện — chẳng hạn ràng buộc mỗi sinh viên chỉ có một chương trình đào tạo chính. Những thứ này SQLite không
có, hoặc có với ngữ nghĩa khác. Dùng hai hệ quản trị cho hai môi trường sẽ dẫn tới kiểm thử xanh mà chạy
thật thì sai, nên `src/data/db/build.py` từ chối mọi hệ quản trị khác.

Hệ quả: chạy kiểm thử cần một máy chủ PostgreSQL. Nhóm chạy nó bằng Docker theo cấu hình trong
`build/deploy/`, nên phiên bản và cấu hình giống nhau giữa các máy và giống dịch vụ mà CI dựng lên.

### SQLAlchemy Core, không dùng ORM

`src/data/db/schema.py` khai báo bảng bằng `Table(...)` và là nguồn sự thật duy nhất cho cấu trúc dữ liệu.
Hệ thống đọc nhiều hơn ghi, và các truy vấn đều trả về bảng để tính toán theo lô, nên lớp đối tượng của
ORM không mang lại lợi ích, trong khi làm khó việc đọc ra SQL thực sự được chạy.

Toàn bộ SQL nằm trong `src/data`. `Repository` là cửa duy nhất mà tầng nghiệp vụ đi qua, nên không có câu
SQL nào rải rác trong code xử lý luật học vụ hay code API.

### Migration bằng Alembic từ v2

Tới v1, lược đồ được dựng lại từ `schema.py` và dữ liệu nạp lại từ CSV, nên chưa cần migration. v2 lưu tài
khoản, bảng điểm và kế hoạch của sinh viên thật: dữ liệu đó không sinh lại được, nên lược đồ đổi qua Alembic
(`migrations/`, `python -m tools.migrate`).

- `schema.py` vẫn là nguồn sự thật duy nhất. Migration được sinh từ nó (`python -m tools.new_migration`), và
  `test/test_migrations.py` kiểm migration luôn ra đúng `schema.py`.
- Bảng người dùng (`USER_TABLES`) không có khóa ngoại tới bảng tham chiếu, chỉ ghi mã tự nhiên. Nhờ vậy dữ liệu
  tham chiếu vẫn nạp lại được từ CSV (`tools.build_db --production --reload-reference`) mà không đụng dữ liệu
  người dùng.
- `app_settings.schema_version` vẫn ghi phiên bản lược đồ; `RETIRED_TABLES` vẫn dọn bảng đã bỏ ở database
  dựng bằng `build()`; `data/schema/schema_postgresql.sql` vẫn được sinh để đọc và review.

### Xếp hạng dựa trên quy tắc, không dùng thư viện học máy

Mọi gợi ý phải truy được về tiêu chí và dữ liệu đã tạo ra nó; cùng một đầu vào phải cho cùng một kết quả
để kiểm thử được; và ràng buộc học vụ là luật, không phải thứ để một mô hình đoán. Vì vậy `requirements.txt`
không có thư viện học máy nào. Lập luận đầy đủ: mục *Vì sao chọn cách tiếp cận dựa trên quy tắc* trong
`README.md`.

### Phụ thuộc ghi phiên bản tối thiểu, không có file lock

`requirements.txt` chỉ ghi phiên bản tối thiểu. CI cài bản mới nhất thỏa điều kiện, nên một thay đổi phá vỡ
ở thư viện sẽ làm CI đỏ ngay thay vì âm thầm lệch giữa các máy.

Mặt khác của lựa chọn này: hai máy cài ở hai thời điểm có thể nhận phiên bản khác nhau. Khi một thư viện
lên phiên bản lớn và làm vỡ code, cách xử lý là thêm chặn trên cho đúng thư viện đó kèm lý do, không ghim
toàn bộ danh sách.

### Hợp đồng API được khóa bằng CI

Lược đồ PostgreSQL và dữ liệu giả lập đều là file sinh tự động được commit vào repo, và CI sinh lại rồi so
sánh để chúng không thể lệch khỏi code sinh ra chúng. Khi tầng API có endpoint đầu tiên, đặc tả OpenAPI
được khóa bằng đúng cơ chế đó, nên backend không thể đổi API mà hợp đồng vẫn đứng yên.
