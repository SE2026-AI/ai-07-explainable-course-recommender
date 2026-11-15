"""Nạp một file feed JSON của nguồn ngoài vào database, thử lại được mà không ghi lặp.

    python -m tools.ingest_feed --file data/feed/sis-20261-example.json
    python -m tools.ingest_feed --file ... --url postgresql+psycopg://user:pass@host:5432/db
    python -m tools.ingest_feed --file ... --attempts 5          # nguồn đang chập chờn

Chạy lại cùng một file là an toàn: lần thứ hai in "đã áp dụng" và không ghi thêm dòng nào.
Định dạng feed: {"batch_id": "...", "source": "...", "rows": [{"university_code": ...}, ...]}.
"""
import argparse
import json
import sys

from src.data.db.build import get_engine
from src.data.ingest import Batch, PostgresRegistrationStore, RetryPolicy, ingest_batch


def read_batch(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return Batch(data["batch_id"], data.get("source", "sis"), tuple(data["rows"]))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="file feed JSON của nguồn ngoài")
    ap.add_argument("--url", default=None, help="mặc định: biến môi trường DATABASE_URL")
    ap.add_argument("--attempts", type=int, default=3)
    a = ap.parse_args()

    batch = read_batch(a.file)
    engine = get_engine(a.url)
    try:
        store = PostgresRegistrationStore(engine)
        out = ingest_batch(batch, store, RetryPolicy(attempts=a.attempts))
    finally:
        engine.dispose()

    trang_thai = "đã áp dụng trước đó" if out.already_applied else "ghi mới"
    print(f"batch {out.batch_id}: {trang_thai}, {out.rows_written} dòng, {out.attempts} lần gọi")


if __name__ == "__main__":
    main()
