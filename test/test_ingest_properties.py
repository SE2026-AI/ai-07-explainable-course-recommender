"""Test theo tính chất (property-based) cho vòng retry: đúng với MỌI batch và MỌI lịch lỗi.

Vì sao chọn property-based: rủi ro không nằm ở một dữ liệu cụ thể mà ở tổ hợp (nội dung batch x
thời điểm lỗi xảy ra). Viết tay vài ca là bỏ sót; `hypothesis` sinh tổ hợp và tự thu nhỏ phản ví dụ.

Chọn dữ liệu:
- Trường dữ liệu lấy từ miền hợp lệ thật: `status` chỉ trong ba giá trị mà ràng buộc CHECK của
  `course_registrations` cho phép, mã sinh viên / học phần lấy từ một tập nhỏ để batch có khả năng
  chứa dòng trùng nhau - đúng tình huống đáng lo khi retry.
- Lịch lỗi là danh sách "ok" / "transient" dài tối đa 6, bao được mọi vị trí lỗi trong trần 3 lần gọi.
- `derandomize=True` để CI chạy lại ra đúng kết quả; hai `@example` cố định giữ ca biên (batch rỗng,
  lỗi liên tục) luôn được chạy.

Không cần database. Store trong bộ nhớ được tạo MỚI trong từng ví dụ: dùng chung một store giữa các
ví dụ của `@given` là nguồn flaky kinh điển (ví dụ sau nhìn thấy dữ liệu của ví dụ trước).
"""
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st
from ingest_contract import assert_store_contract

from src.data.ingest import (
    AttemptLog,
    Batch,
    MemoryBatchStore,
    PermanentFailure,
    RetryPolicy,
    TransientFailure,
    ingest_batch,
)

POLICY = RetryPolicy(attempts=3, base_delay=0.0, max_delay=0.0, budget=10.0)


def no_sleep(_seconds):
    """Không chờ thật: giữ test nhanh và không phụ thuộc đồng hồ."""


row = st.fixed_dictionaries({
    "university_code": st.just("HUS"),
    "student_code": st.sampled_from(["26000001", "26000002", "26000003"]),
    "course_code": st.sampled_from(["MAT2400", "MAT2503", "HUS1011", "PHI1006"]),
    "term_code": st.sampled_from(["20261", "20262"]),
    "status": st.sampled_from(["planned", "registered", "dropped"]),
})
rows = st.lists(row, max_size=6)
schedule = st.lists(st.sampled_from(["ok", "transient"]), max_size=6)

ONE_ROW = [{"university_code": "HUS", "student_code": "26000001", "course_code": "MAT2400",
            "term_code": "20261", "status": "registered"}]


def failures(schedule_):
    return [TransientFailure("máy chủ nguồn đang quá tải") if s == "transient" else None for s in schedule_]


def first_ok(schedule_):
    """Lần gọi đầu tiên không gặp lỗi (lịch hết cũng coi là thành công)."""
    return schedule_.index("ok") if "ok" in schedule_ else len(schedule_)


@settings(derandomize=True, deadline=None, max_examples=80)
@given(rows=rows, sched=schedule)
@example(rows=[], sched=[])
@example(rows=ONE_ROW, sched=["transient", "transient", "transient"])
@example(rows=ONE_ROW + ONE_ROW, sched=["transient", "ok"])
def test_du_retry_bao_nhieu_lan_du_lieu_cung_chi_duoc_ghi_mot_lan(rows, sched):
    """Bất biến chính của VT-096: side effect không được lặp, và thất bại không để lại dấu vết."""
    store = MemoryBatchStore(failures=failures(sched))
    batch = Batch("sis-20261-0001", "sis", tuple(rows))
    log = AttemptLog()

    can_succeed = first_ok(sched) + 1 <= POLICY.attempts
    if not can_succeed:
        with pytest.raises(TransientFailure):
            ingest_batch(batch, store, POLICY, no_sleep, log)
        assert store.rows == [], "lần nạp thất bại không được để lại dòng nào"
        assert log.attempts == POLICY.attempts
        return

    out = ingest_batch(batch, store, POLICY, no_sleep, log)
    assert out.applied and not out.already_applied
    assert out.rows_written == len(rows)
    assert out.attempts == first_ok(sched) + 1
    assert store.rows == list(rows)

    lai = ingest_batch(batch, store, POLICY, no_sleep)
    assert lai.already_applied and lai.rows_written == 0
    assert store.rows == list(rows), "gọi lại cùng batch_id không được ghi thêm"


@settings(derandomize=True, deadline=None, max_examples=40)
@given(rows=rows, sched=schedule)
def test_so_lan_goi_luon_trong_tran(rows, sched):
    store = MemoryBatchStore(failures=failures(sched))
    log = AttemptLog()
    try:
        ingest_batch(Batch("sis-20261-0002", "sis", tuple(rows)), store, POLICY, no_sleep, log)
    except TransientFailure:
        pass
    assert 1 <= log.attempts <= POLICY.attempts
    assert store.calls == log.attempts


@settings(derandomize=True, deadline=None, max_examples=40)
@given(rows=rows)
def test_loi_vinh_vien_chi_goi_mot_lan_va_khong_ghi_gi(rows):
    store = MemoryBatchStore(failures=[PermanentFailure("mã học phần không tồn tại")])
    with pytest.raises(PermanentFailure):
        ingest_batch(Batch("sis-20261-0003", "sis", tuple(rows)), store, POLICY, no_sleep)
    assert store.calls == 1
    assert store.rows == []


@settings(derandomize=True, deadline=None, max_examples=40)
@given(a=rows, b=rows)
def test_cung_batch_id_khac_noi_dung_bi_tu_choi(a, b):
    """Nguồn gửi lại cùng `batch_id` với nội dung khác là lỗi của nguồn, không phải retry."""
    if a == b:
        return
    store = MemoryBatchStore()
    ingest_batch(Batch("sis-20261-0004", "sis", tuple(a)), store, POLICY, no_sleep)
    with pytest.raises(PermanentFailure):
        ingest_batch(Batch("sis-20261-0004", "sis", tuple(b)), store, POLICY, no_sleep)
    assert store.rows == list(a)


class NonAtomicStore:
    """Store ghi dữ liệu TRƯỚC rồi mới chết - đúng kiểu failure từng phần mà VT-096 lo.

    Dùng để kiểm tra chính bài test: nếu tính chất ở trên vẫn xanh với store này thì nó vô nghĩa.
    """

    def __init__(self, failures=()):
        self.rows = []
        self.ledger = {}
        self.calls = 0
        self._failures = list(failures)

    def apply(self, batch):
        self.calls += 1
        self.rows.extend(batch.rows)
        failure = self._failures.pop(0) if self._failures else None
        if failure is not None:
            raise failure
        self.ledger[batch.batch_id] = batch.checksum
        return len(batch.rows)


def test_tinh_chat_nay_bat_duoc_store_ghi_nua_voi():
    """Ai kiểm bài kiểm? Cho tính chất chạy trên một store cố ý hỏng và khẳng định nó đỏ."""
    store = NonAtomicStore(failures=[TransientFailure("mất kết nối sau khi đã ghi")])
    batch = Batch("sis-20261-0005", "sis", tuple(ONE_ROW))
    out = ingest_batch(batch, store, POLICY, no_sleep)
    assert out.applied
    assert len(store.rows) == 2 * len(ONE_ROW), "store nửa vời ghi hai lần, tính chất phải thấy"
    assert store.rows != list(ONE_ROW)


def test_hop_dong_store_dung_tren_store_bo_nho():
    """Cùng bộ khẳng định sẽ chạy lại trên PostgreSQL ở `test_ingest_postgres.py`."""
    store = MemoryBatchStore()
    batch = Batch("sis-20261-0006", "sis", tuple(ONE_ROW))
    conflicting = Batch("sis-20261-0006", "sis", ())
    assert_store_contract(store, batch, conflicting, lambda: len(store.rows))
