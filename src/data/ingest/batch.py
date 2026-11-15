"""Một batch dữ liệu từ nguồn ngoài và quy tắc chỉ-ghi-một-lần của nó."""
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Protocol

from .retry import DEFAULT_POLICY, AttemptLog, run_with_retry


@dataclass(frozen=True)
class Batch:
    """Một lần gửi của nguồn ngoài. `batch_id` do nguồn đặt và là khóa chống ghi lặp."""

    batch_id: str
    source: str
    rows: tuple

    @property
    def checksum(self):
        """Băm nội dung đã chuẩn hóa: để phát hiện cùng `batch_id` mà khác nội dung."""
        payload = json.dumps([dict(sorted(r.items())) for r in self.rows],
                             sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AlreadyApplied(Exception):
    """Batch đã được ghi trước đó. Không phải lỗi: là câu trả lời của sổ ghi batch."""

    def __init__(self, batch_id, rows=0):
        super().__init__(f"batch {batch_id!r} đã được áp dụng ({rows} dòng)")
        self.batch_id = batch_id
        self.rows = rows


@dataclass(frozen=True)
class IngestOutcome:
    """Kết quả một lần nạp. `rows_written` là số dòng lần gọi NÀY ghi, nên bằng 0 khi batch đã có."""

    batch_id: str
    applied: bool
    already_applied: bool
    rows_written: int
    attempts: int


class BatchStore(Protocol):
    """Nơi ghi dữ liệu. Hợp đồng: `apply` nguyên tử và từ chối `batch_id` đã ghi."""

    def apply(self, batch) -> int:
        ...


def ingest_batch(batch, store, policy=DEFAULT_POLICY, sleep=time.sleep, log=None):
    """Nạp `batch` qua `store`: thử lại khi lỗi tạm thời, nhưng dữ liệu chỉ được ghi một lần.

    Hai cơ chế nằm ở hai chỗ khác nhau và đó là chủ ý:
    - Retry ở đây, tại biên gọi ra ngoài, vì chỉ ở đây mới biết lỗi nào đáng thử lại.
    - Bảo đảm chỉ-ghi-một-lần ở `store`, bằng khóa duy nhất trên `batch_id`. Retry an toàn
      chính vì store nhận ra batch cũ; không có nó thì mỗi lần thử lại là một lần ghi lặp.

    `AlreadyApplied` không phải lỗi mà là câu trả lời "đã có rồi", nên không được thử lại.
    """
    log = AttemptLog() if log is None else log

    def step():
        try:
            return store.apply(batch)
        except AlreadyApplied as exc:
            return exc

    ket_qua = run_with_retry(step, policy, sleep, log)
    if isinstance(ket_qua, AlreadyApplied):
        return IngestOutcome(batch.batch_id, applied=False, already_applied=True,
                             rows_written=0, attempts=log.attempts)
    return IngestOutcome(batch.batch_id, applied=True, already_applied=False,
                         rows_written=ket_qua, attempts=log.attempts)
