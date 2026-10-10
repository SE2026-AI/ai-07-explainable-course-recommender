# Tools

Các script dùng khi phát triển: nạp dữ liệu, sinh dữ liệu giả lập, xuất file để đọc. Mọi script chạy từ
**thư mục gốc của dự án** dưới dạng module, ví dụ `python -m tools.build_db`.

Cài đặt môi trường: `test/README.md`. Không script nào chứa mật khẩu hay địa chỉ máy chủ thật; địa chỉ
database luôn lấy từ `DATABASE_URL`.

---

## Danh sách

| Script | Đọc | Ghi | Ghi vào database |
| --- | --- | --- | --- |
| `build_db.py` | `data/seed`, `data/synthetic` | – | Có: xóa và tạo lại database đang trỏ tới |
| `generate_synthetic.py` | `data/seed` | `data/synthetic/*.csv` | Không: tự tạo database tạm rồi xóa |
| `generate_fixtures.py` | `data/seed`, `test/fixtures/seed_demo` | `test/fixtures/students/*.csv` | Không: tự tạo database tạm rồi xóa |
| `export_schema.py` | `src/data/db/` | `data/schema/schema_postgresql.sql` | Không |
| `export_excel.py` | database đang trỏ tới | `data/xem_du_lieu.xlsx` | Không |

---

## `build_db.py` — nạp CSV vào database

```bash
python -m tools.build_db                                        # seed + synthetic
python -m tools.build_db --dirs data/seed                        # chỉ dữ liệu chương trình đào tạo
python -m tools.build_db --url postgresql+psycopg://u:p@host:5432/db
```

**Xóa và tạo lại toàn bộ bảng** rồi nạp lại từ CSV, in số dòng theo từng bảng. Dùng sau mỗi lần sửa CSV
hoặc sửa lược đồ.

CSV dùng mã nghiệp vụ (`course_code`, `curriculum_code`…) cho dễ đọc và dễ sửa bằng tay; khi nạp, mã được
đổi sang `id` của bảng đích. Thứ tự nạp do `LOAD_ORDER` trong `src/data/db/build.py` quyết định, nên một
thư mục chỉ chứa một phần các file vẫn nạp được và nhiều thư mục ghép được với nhau.

---

## `generate_synthetic.py` — sinh sinh viên giả lập

```bash
python -m tools.generate_synthetic
```

Sinh sinh viên và toàn bộ quá trình học của họ cho **mọi** chương trình đào tạo đang ở trạng thái `active`,
ghi ra `data/synthetic/`. Script tự dựng một database tạm từ `data/seed` nên không đụng tới database đang
dùng, nhưng vẫn cần container PostgreSQL đang chạy (xem `test/README.md`).

Dữ liệu tuân thủ quy chế: chỉ học khi đủ điều kiện tiên quyết, trượt thì học lại, không vượt số tín chỉ
tối đa mỗi kỳ. Mỗi sinh viên có năng lực chung và điểm mạnh theo chủ đề (ẩn, không ghi ra CSV) nên nhìn
điểm các môn đã học là đoán được sinh viên mạnh chủ đề nào — đó là tín hiệu để thuật toán xếp hạng dựa vào.

Tham số nằm ngay đầu file: `STUDENTS_PER_CURRICULUM`, `HAT_GIONG` (hạt giống ngẫu nhiên), các trọng số
ảnh hưởng tới việc chọn môn tự chọn.

**Cùng `HAT_GIONG` thì mỗi lần chạy ra file giống hệt nhau.** Đổi tham số hoặc đổi code sinh dữ liệu thì
phải chạy lại script và commit file CSV mới; CI kiểm tra điều này.

Mã sinh viên sinh ra có 8 chữ số theo khóa, ví dụ khóa 2025 → `25000001`.

---

## `generate_fixtures.py` — sinh bộ sinh viên kiểm thử

```bash
python -m tools.generate_fixtures
```

Sinh các sinh viên kiểm thử cố định (`T01`, `T02`, …) và **trạng thái mong đợi của từng học phần** cho mỗi
sinh viên, ghi ra `test/fixtures/students/`. Khác với dữ liệu giả lập ở chỗ mỗi ca được thiết kế cho một
tình huống cụ thể: trượt rồi chưa học lại, điểm đúng ngưỡng đạt, được miễn môn nhờ chứng chỉ, khối tự chọn
đã đủ tín chỉ, hai trường trùng mã sinh viên…

Danh sách ca nằm trong hằng `CASES` ngay đầu file. Thêm một ca mới: thêm một phần tử vào `CASES` rồi chạy
lại script.

File `expected_course_status.csv` là **đáp án** để kiểm thử tầng luật học vụ: mỗi dòng là trạng thái đúng
của một học phần đối với một sinh viên, dùng đúng tập giá trị mà API trả về. File `course_registrations.csv`
là các môn sinh viên sẽ đăng ký nếu học đúng kế hoạch, dùng để đo độ chính xác của gợi ý.

Bộ này cũng nạp thêm trường giả lập `DEMO` trong `test/fixtures/seed_demo/`, vốn tồn tại để chứng minh hệ
thống không viết cứng mã trường, mã học phần hay ngưỡng điểm đạt nào.

---

## `export_schema.py` — xuất câu lệnh tạo bảng

```bash
python -m tools.export_schema
```

Sinh `data/schema/schema_postgresql.sql` từ `src/data/db/schema.py` và `src/data/db/views.py`, để đọc và
review bằng mắt hoặc chạy tay khi cần. **Không sửa file SQL đó** — sửa `schema.py` rồi chạy lại script.

Phải chạy lại sau mỗi lần đổi lược đồ, và commit kèm theo; CI kiểm tra file này khớp với code.

---

## `export_excel.py` — xuất dữ liệu ra Excel

```bash
python -m tools.export_excel
```

Xuất mọi bảng và view của database đang trỏ tới ra `data/xem_du_lieu.xlsx`, mỗi bảng một sheet, kèm sheet
tổng quan số dòng. Dùng để đối chiếu dữ liệu với văn bản chương trình đào tạo, hoặc để người không dùng
terminal xem được dữ liệu.

File kết quả **không được commit** (đã có trong `.gitignore`). Muốn sửa dữ liệu thì sửa CSV trong
`data/seed`, không sửa file Excel.

---

## Khi nào phải chạy lại script nào

| Vừa thay đổi | Chạy lại |
| --- | --- |
| CSV trong `data/seed` | `build_db`, rồi `generate_synthetic` và `generate_fixtures` nếu thay đổi ảnh hưởng tới khung chương trình |
| Lược đồ (`src/data/db/schema.py`, `views.py`) | `export_schema`, `build_db` |
| Code sinh dữ liệu (`src/data/synthetic.py`, `tools/generate_*.py`) | `generate_synthetic`, `generate_fixtures` |
| Lược đồ hoặc dữ liệu, trước khi mở pull request | `pytest` |

Chuỗi lệnh dựng lại tất cả từ đầu:

```bash
python -m tools.export_schema
python -m tools.generate_synthetic
python -m tools.generate_fixtures
python -m tools.build_db
pytest
```

CI chạy đúng các script này (theo thứ tự riêng của nó) rồi `git diff --exit-code`; nếu `git diff` sau khi
chạy lại không rỗng thì có file sinh tự động chưa được commit.
