"""Nạp dữ liệu từ dịch vụ ngoài: thử lại khi lỗi tạm thời, nhưng chỉ ghi đúng một lần.

Xem `src/data/ingest/README.md`.
"""
from .batch import AlreadyApplied, Batch, BatchStore, IngestOutcome, ingest_batch
from .memory import MemoryBatchStore
from .postgres import PostgresRegistrationStore
from .retry import AttemptLog, PermanentFailure, RetryPolicy, TransientFailure, run_with_retry

__all__ = [
    "AlreadyApplied", "AttemptLog", "Batch", "BatchStore", "IngestOutcome", "MemoryBatchStore",
    "PermanentFailure", "PostgresRegistrationStore", "RetryPolicy", "TransientFailure",
    "ingest_batch", "run_with_retry",
]
