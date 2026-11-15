"""Harness đo tải cho vòng nạp batch: nhiều tác vụ đồng thời, đo p95, kiểm bất biến sau khi xong.

    python -m tools.ingest_load                                  # 120 tác vụ, store PostgreSQL
    python -m tools.ingest_load --store memory                   # chỉ đo phần logic, không chạm database
    python -m tools.ingest_load --tasks 120 --transient-rate 0.3 --latency 0.15 --duplicate-rate 0.2

Mô hình: mỗi tác vụ là một batch 3 dòng đăng ký. Store thật được bọc bởi `FlakyStore` để thêm
độ trễ của dịch vụ ngoài và tỷ lệ lỗi tạm thời, nên vòng retry thật (có chờ thật) được đo.
`--duplicate-rate` phần tác vụ gửi lại `batch_id` đã có, để đo luôn đường "đã áp dụng".

Giới hạn của phép đo, phải đọc kèm số: database là PostgreSQL trong Docker trên cùng máy (không
qua mạng), nguồn ngoài là độ trễ giả lập chứ không phải dịch vụ thật, và tác vụ chạy bằng thread
trong một tiến trình Python nên có ảnh hưởng của GIL. Con số ở đây nói về vòng retry và về
database, không nói về toàn hệ thống dưới tải thật.
"""
import argparse
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, text

from src.data.db.build import build, temporary_database
from src.data.ingest import (
    Batch,
    MemoryBatchStore,
    PostgresRegistrationStore,
    RetryPolicy,
    TransientFailure,
    ingest_batch,
)

FOLDERS = ["data/seed", "data/synthetic"]
ROWS_PER_BATCH = 3


class FlakyStore:
    """Bọc một store: thêm độ trễ của dịch vụ ngoài và tỷ lệ lỗi tạm thời."""

    def __init__(self, inner, latency, transient_rate, seed=7):
        self.inner = inner
        self.latency = latency
        self.transient_rate = transient_rate
        self._rng = random.Random(seed)

    def seen(self, batch):
        return self.inner.seen(batch)

    def apply(self, batch):
        time.sleep(self.latency)
        if self._rng.random() < self.transient_rate:
            raise TransientFailure("nguồn ngoài trả 503")
        return self.inner.apply(batch)


def candidate_rows(engine, need):
    """Các dòng (sinh viên, học phần, học kỳ) hợp lệ mà database chưa có, lấy từ dữ liệu thật."""
    with engine.connect() as conn:
        uni = conn.execute(text("SELECT code FROM universities ORDER BY id LIMIT 1")).scalar()
        term = conn.execute(text(
            "SELECT t.code FROM terms t JOIN universities u ON u.id = t.university_id "
            "WHERE u.code = :u ORDER BY t.code DESC LIMIT 1"), {"u": uni}).scalar()
        pairs = conn.execute(text(
            "SELECT s.student_code, c.code FROM students s "
            "JOIN universities u ON u.id = s.university_id "
            "JOIN courses c ON c.university_id = u.id "
            "WHERE u.code = :u "
            "AND NOT EXISTS (SELECT 1 FROM course_registrations r "
            "                WHERE r.student_id = s.id AND r.course_id = c.id) "
            "AND NOT EXISTS (SELECT 1 FROM course_results x "
            "                WHERE x.student_id = s.id AND x.course_id = c.id) "
            "ORDER BY s.id, c.code LIMIT :n"), {"u": uni, "n": need}).all()
    if len(pairs) < need:
        raise SystemExit(f"dữ liệu chỉ có {len(pairs)} cặp trống, cần {need}")
    return [{"university_code": uni, "student_code": sv, "course_code": mh,
             "term_code": str(term), "status": "planned"} for sv, mh in pairs]


def make_batches(rows, tasks, duplicate_rate, seed=11):
    """Mỗi tác vụ một batch; một phần tác vụ dùng lại `batch_id` của tác vụ trước đó."""
    rng = random.Random(seed)
    batches, moc = [], []
    for i in range(tasks):
        if moc and rng.random() < duplicate_rate:
            batches.append(rng.choice(moc))
            continue
        phan = rows[len(moc) * ROWS_PER_BATCH:(len(moc) + 1) * ROWS_PER_BATCH]
        batch = Batch(f"sis-load-{i:04d}", "sis", tuple(phan))
        moc.append(batch)
        batches.append(batch)
    return batches


def run(batches, store, policy, workers):
    def one(batch):
        t0 = time.perf_counter()
        try:
            out = ingest_batch(batch, store, policy)
            return time.perf_counter() - t0, out, None
        except Exception as exc:                      # noqa: BLE001 - harness cần đếm mọi lỗi
            return time.perf_counter() - t0, None, exc

    bat_dau = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        ket_qua = list(pool.map(one, batches))
    return ket_qua, time.perf_counter() - bat_dau


def report(ket_qua, tong_thoi_gian, batches, target_p95):
    thoi_gian = sorted(t for t, _, _ in ket_qua)
    p = statistics.quantiles(thoi_gian, n=100, method="inclusive")
    ghi_moi = sum(1 for _, o, _ in ket_qua if o is not None and o.applied)
    da_co = sum(1 for _, o, _ in ket_qua if o is not None and o.already_applied)
    loi = [e for _, _, e in ket_qua if e is not None]
    print(f"tác vụ                 {len(ket_qua)}")
    print(f"batch_id khác nhau     {len({b.batch_id for b in batches})}")
    print(f"ghi mới / đã áp dụng   {ghi_moi} / {da_co}")
    print(f"thất bại               {len(loi)}" + (f"  ({type(loi[0]).__name__}: {loi[0]})" if loi else ""))
    print(f"p50                    {thoi_gian[len(thoi_gian) // 2]:.3f} s")
    print(f"p95                    {p[94]:.3f} s   (mục tiêu {target_p95:.1f} s)")
    print(f"max                    {thoi_gian[-1]:.3f} s")
    print(f"tổng thời gian         {tong_thoi_gian:.2f} s -> {len(ket_qua) / tong_thoi_gian:.1f} tác vụ/giây")
    print(f"kết luận p95           {'ĐẠT' if p[94] <= target_p95 else 'KHÔNG ĐẠT'}")
    return ghi_moi, da_co, loi


def check_invariant(engine, batches, ket_qua):
    """Sau tải: mỗi batch_id ĐÃ GHI có đúng một dòng sổ, và batch thất bại không để lại dấu vết.

    Batch cạn lượt thử lại là chuyện bình thường dưới tải; điều phải đúng là nó không ghi nửa vời.
    """
    da_ghi = {o.batch_id for _, o, _ in ket_qua if o is not None and o.applied}
    khong_xong = sorted({b.batch_id for b in batches} - da_ghi)
    with engine.connect() as conn:
        so = conn.execute(text("SELECT count(*), count(DISTINCT batch_id) FROM ingest_batches")).one()
        dong = conn.execute(text(
            "SELECT count(*) FROM course_registrations WHERE source = 'imported'")).scalar()
        sot = conn.execute(text("SELECT count(*) FROM ingest_batches WHERE batch_id = ANY(:ids)"),
                           {"ids": khong_xong}).scalar() if khong_xong else 0
    ok = so[0] == so[1] == len(da_ghi) and dong == len(da_ghi) * ROWS_PER_BATCH and sot == 0
    print(f"sổ ghi batch           {so[0]} dòng, {so[1]} batch_id khác nhau (cần {len(da_ghi)})")
    print(f"dòng đã nhập           {dong} (cần {len(da_ghi) * ROWS_PER_BATCH})")
    print(f"batch cạn lượt thử     {len(khong_xong)}, số dòng sót lại trong sổ: {sot}")
    print(f"bất biến ghi-một-lần   {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=int, default=120, help="số tác vụ đồng thời (VT-096: 120)")
    ap.add_argument("--store", choices=["postgres", "memory"], default="postgres")
    ap.add_argument("--latency", type=float, default=0.15, help="độ trễ giả lập của nguồn ngoài, giây")
    ap.add_argument("--transient-rate", type=float, default=0.3)
    ap.add_argument("--duplicate-rate", type=float, default=0.2)
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--target-p95", type=float, default=3.5, help="mục tiêu p95 của biến thể, giây")
    a = ap.parse_args()

    policy = RetryPolicy(attempts=a.attempts)
    can = a.tasks * ROWS_PER_BATCH

    if a.store == "memory":
        rows = [{"university_code": "HUS", "student_code": f"2600{i:04d}", "course_code": f"C{i:04d}",
                 "term_code": "20261", "status": "planned"} for i in range(can)]
        batches = make_batches(rows, a.tasks, a.duplicate_rate)
        store = FlakyStore(MemoryBatchStore(), a.latency, a.transient_rate)
        ket_qua, tong = run(batches, store, policy, a.tasks)
        report(ket_qua, tong, batches, a.target_p95)
        return

    with temporary_database() as url:
        nap, _ = build(url, FOLDERS)
        nap.dispose()
        engine = create_engine(url, pool_size=min(a.tasks, 64), max_overflow=0, pool_timeout=60)
        try:
            batches = make_batches(candidate_rows(engine, can), a.tasks, a.duplicate_rate)
            store = FlakyStore(PostgresRegistrationStore(engine), a.latency, a.transient_rate)
            ket_qua, tong = run(batches, store, policy, a.tasks)
            report(ket_qua, tong, batches, a.target_p95)
            check_invariant(engine, batches, ket_qua)
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
