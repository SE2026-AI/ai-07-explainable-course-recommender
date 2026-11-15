"""Hợp đồng mà MỌI `BatchStore` phải giữ, dùng cho cả store bộ nhớ và store PostgreSQL.

Không có file này thì các test tính chất chạy trên store bộ nhớ không nói được gì về store thật.
"""
import pytest

from src.data.ingest import AlreadyApplied, PermanentFailure


def assert_store_contract(store, batch, conflicting, count_rows):
    """`batch` ghi được một lần; gọi lại là `AlreadyApplied`; cùng id khác nội dung là `PermanentFailure`.

    `conflicting` phải có cùng `batch_id` với `batch` nhưng nội dung khác.
    `count_rows()` trả về số dòng dữ liệu mà store đang giữ.
    """
    assert batch.batch_id == conflicting.batch_id
    assert batch.checksum != conflicting.checksum

    assert store.apply(batch) == len(batch.rows)
    assert count_rows() == len(batch.rows)

    with pytest.raises(AlreadyApplied):
        store.apply(batch)
    assert count_rows() == len(batch.rows), "gọi lại batch cũ không được ghi thêm dòng nào"

    with pytest.raises(PermanentFailure):
        store.apply(conflicting)
    assert count_rows() == len(batch.rows), "batch trùng id khác nội dung không được ghi gì"
