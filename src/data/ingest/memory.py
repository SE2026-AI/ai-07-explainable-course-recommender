"""Store trong bộ nhớ: dùng cho test tính chất và harness đo tải, không dùng lúc chạy thật.

Nó phải tuân đúng hợp đồng `BatchStore` như bản PostgreSQL, nếu không mọi test chạy trên
nó đều vô nghĩa. `test/ingest_contract.py` là bộ khẳng định chạy cho cả hai store.
"""
import threading

from .batch import AlreadyApplied
from .retry import PermanentFailure


class MemoryBatchStore:
    """Giả lập một store nguyên tử có sổ ghi batch.

    `failures` là lịch lỗi: phần tử thứ i được nâng lên ở lần `apply` thứ i, `None` là thành công.
    Lỗi được nâng lên SAU khi dữ liệu đã được chuẩn bị nhưng TRƯỚC khi ghi vào `rows` và sổ, đúng
    như một transaction bị rollback.
    """

    def __init__(self, failures=()):
        self.rows = []
        self.ledger = {}
        self.calls = 0
        self._failures = list(failures)
        self._lock = threading.Lock()

    def seen(self, batch):
        """(checksum, số dòng) nếu batch đã ghi, `None` nếu chưa."""
        return self.ledger.get(batch.batch_id)

    def apply(self, batch):
        with self._lock:
            self.calls += 1
            ghi_nhan = self.ledger.get(batch.batch_id)
            if ghi_nhan is not None:
                if ghi_nhan[0] != batch.checksum:
                    raise PermanentFailure(
                        f"batch {batch.batch_id!r} đã ghi với nội dung khác: nguồn gửi trùng mã")
                raise AlreadyApplied(batch.batch_id, ghi_nhan[1])

            staged = list(batch.rows)
            failure = self._failures.pop(0) if self._failures else None
            if failure is not None:
                raise failure

            self.ledger[batch.batch_id] = (batch.checksum, len(staged))
            self.rows.extend(staged)
            return len(staged)
