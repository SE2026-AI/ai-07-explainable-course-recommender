"""Store trong bộ nhớ: dùng cho test tính chất và harness đo tải, không dùng lúc chạy thật.

Nó phải tuân đúng hợp đồng `BatchStore` như bản PostgreSQL, nếu không mọi test chạy trên
nó đều vô nghĩa. `test/test_ingest_store_contract.py` chạy cùng một bộ tình huống trên cả
hai store để giữ hai bản khớp nhau.
"""
import threading


class MemoryBatchStore:
    """BƯỚC ĐẦU - hành vi hôm nay: ghi thêm vào cuối, không sổ ghi batch, nên gọi lại là ghi lặp.

    `failures` là lịch lỗi: phần tử thứ i được nâng lên ở lần `apply` thứ i, `None` là thành công.
    """

    def __init__(self, failures=()):
        self.rows = []
        self.ledger = {}
        self.calls = 0
        self._failures = list(failures)
        self._lock = threading.Lock()

    def seen(self, batch):
        """BƯỚC ĐẦU - chưa có sổ ghi batch nên không bao giờ nhận ra batch cũ."""
        return None

    def apply(self, batch):
        with self._lock:
            self.calls += 1
            failure = self._failures.pop(0) if self._failures else None
            if failure is not None:
                raise failure
            self.rows.extend(batch.rows)
            return len(batch.rows)
