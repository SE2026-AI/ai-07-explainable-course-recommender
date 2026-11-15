# Nạp dữ liệu từ nguồn ngoài (`src/data/ingest/`)

Change request: **thêm khả năng retry khi dịch vụ ngoài tạm lỗi, nhưng không được lặp side effect.**
Rủi ro trọng tâm: **failure từng phần để lại trạng thái dữ liệu không nhất quán.**

Trước thay đổi này, đường ghi duy nhất của dự án là `load_directory()` trong `src/data/db/build.py`:
không có retry, và chạy lại trên cùng dữ liệu thì hoặc chết vì trùng khóa hoặc ghi lặp ở bảng không
có ràng buộc duy nhất. Không có cách nào phân biệt "đã nạp rồi" với "dữ liệu sai".

## Thiết kế

| Thành phần | Trách nhiệm | Không làm |
| --- | --- | --- |
| `retry.py` | Phân loại lỗi tạm thời / vĩnh viễn, vòng thử lại có trần số lần và trần thời gian | Biết gì về database |
| `batch.py` | `Batch` (có checksum), `IngestOutcome`, và `ingest_batch()` nối retry với store | Ghi dữ liệu |
| `postgres.py` | Ghi sổ batch + dữ liệu trong **một** transaction, nhận ra batch cũ | Quyết định có thử lại hay không |
| `memory.py` | Store giả lập cùng hợp đồng, cho test tính chất và harness tải | Dùng lúc chạy thật |

Hai cơ chế nằm ở hai nơi khác nhau, đó là chủ ý:

- **Retry** ở biên gọi ra ngoài (`ingest_batch`), vì chỉ ở đó mới biết lỗi nào đáng thử lại.
- **Chỉ-ghi-một-lần** ở store, bằng khóa duy nhất `uq_ingest_batches_batch_id` trong database.
  Retry an toàn *chính vì* store nhận ra batch cũ; nếu đặt kiểm tra này ở tầng gọi thì hai worker
  nạp cùng lúc vẫn ghi hai lần.

Bất biến được bảo vệ: **với mỗi `batch_id`, dữ liệu được ghi trọn vẹn đúng một lần.** Thất bại giữa
đường không để lại dòng nào, vì sổ và dữ liệu chung một transaction. Cùng `batch_id` mà khác nội
dung là lỗi của nguồn (`PermanentFailure`), không phải retry.

## Chạy

```bash
pytest test/test_ingest_retry.py test/test_ingest_properties.py test/test_ingest_postgres.py -v
pytest test/test_ingest_properties.py                      # tính chất, không cần database
pytest --cov=src/data/ingest --cov-branch --cov-report=term-missing \
       test/test_ingest_retry.py test/test_ingest_properties.py test/test_ingest_postgres.py
```

`test_ingest_postgres.py` cần PostgreSQL (`test/README.md`) và tự dựng một database tạm riêng, vì nó
chèn dòng vào `course_registrations` - dùng chung fixture `repo` của cả phiên sẽ làm
`test_student_data.py::test_dang_ky_ky_toi_hop_le` đỏ theo thứ tự chạy.

Nạp một feed thật và đo tải:

```bash
python -m tools.ingest_feed --file data/feed/sis-20261-example.json    # chạy lại không ghi lặp
python -m tools.ingest_load --tasks 120 --target-p95 3.5                # tải riêng của VT-096
python -m tools.ingest_load --store memory                              # chỉ phần logic
```

## Giới hạn hiện tại

- Dữ liệu dừng ở `course_registrations` với `source = 'imported'`. Bước đưa tiếp vào các bảng khác
  (ví dụ `course_results`) chưa làm, nên chưa có bất biến cho bước đó.
- Lỗi tạm thời được nhận ra qua `OperationalError` / `InterfaceError` của SQLAlchemy. Timeout của
  pool (`sqlalchemy.exc.TimeoutError`) **cố ý không** được coi là tạm thời: đó là tín hiệu hết sức
  chứa, thử lại chỉ làm nghẽn thêm.
- Chưa có log có cấu trúc cho `AttemptLog`; hiện mới trả về cho người gọi.
