"""Nạp batch của nguồn ngoài vào PostgreSQL thật: hợp đồng store, failure path, và hai worker đua nhau.

File này tự dựng một database tạm RIÊNG (module-scoped) thay vì dùng fixture `repo`/`repo_all` dùng
chung cả phiên. Lý do: các test ở đây CHÈN dòng vào `course_registrations`, mà
`test_student_data.py::test_dang_ky_ky_toi_hop_le` khẳng định mọi dòng trong bảng đó đều thuộc học kỳ
đang gợi ý. Dùng chung database là tự tạo một test đỏ phụ thuộc thứ tự chạy.
"""
import os
import threading

import pytest
from ingest_contract import assert_store_contract
from sqlalchemy import inspect, text

from src.data.db.build import scratch_build
from src.data.ingest import (
    Batch,
    PermanentFailure,
    PostgresRegistrationStore,
    RetryPolicy,
    TransientFailure,
    ingest_batch,
)

POLICY = RetryPolicy(attempts=3, base_delay=0.0, max_delay=0.0, budget=10.0)
FOLDERS = ["data/seed", "data/synthetic"]


def no_sleep(_seconds):
    """Không chờ thật khi test retry."""


@pytest.fixture(scope="module")
def feed_engine():
    with scratch_build(FOLDERS, os.environ.get("TEST_DATABASE_URL")) as engine:
        yield engine


@pytest.fixture(scope="module")
def feed(feed_engine):
    """Ba dòng đăng ký hợp lệ nhưng CHƯA có trong database, lấy ra từ chính dữ liệu đang có."""
    with feed_engine.connect() as conn:
        sid, uni, student = conn.execute(text(
            "SELECT s.id, u.code, s.student_code FROM students s "
            "JOIN universities u ON u.id = s.university_id ORDER BY s.id LIMIT 1")).one()
        term = conn.execute(text(
            "SELECT t.code FROM terms t JOIN universities u ON u.id = t.university_id "
            "WHERE u.code = :u ORDER BY t.code DESC LIMIT 1"), {"u": uni}).scalar()
        courses = conn.execute(text(
            "SELECT c.code FROM courses c JOIN universities u ON u.id = c.university_id WHERE u.code = :u "
            "AND c.id NOT IN (SELECT course_id FROM course_registrations WHERE student_id = :sid) "
            "AND c.id NOT IN (SELECT course_id FROM course_results WHERE student_id = :sid) "
            "ORDER BY c.code LIMIT 3"), {"u": uni, "sid": sid}).scalars().all()
    assert len(courses) == 3, "dữ liệu không đủ học phần trống để dựng batch kiểm thử"
    return tuple({"university_code": uni, "student_code": student, "course_code": code,
                  "term_code": str(term), "status": "registered"} for code in courses)


def imported_rows(engine):
    with engine.connect() as conn:
        return conn.execute(text("SELECT count(*) FROM course_registrations WHERE source = 'imported'")).scalar()


@pytest.fixture
def store(feed_engine):
    """Store trên database sạch: xóa dấu vết của test trước để các test trong file không phụ thuộc thứ tự."""
    with feed_engine.begin() as conn:
        conn.execute(text("DELETE FROM course_registrations WHERE source = 'imported'"))
        if "ingest_batches" in inspect(feed_engine).get_table_names():
            conn.execute(text("DELETE FROM ingest_batches"))
    return PostgresRegistrationStore(feed_engine)


def test_hop_dong_store_dung_tren_postgres(store, feed, feed_engine):
    """Cùng bộ khẳng định đã chạy cho store bộ nhớ, lần này trên PostgreSQL thật."""
    batch = Batch("sis-20261-0101", "sis", feed)
    conflicting = Batch("sis-20261-0101", "sis", feed[:1])
    assert_store_contract(store, batch, conflicting, lambda: imported_rows(feed_engine))


def test_batch_co_ma_khong_ton_tai_la_loi_vinh_vien(store, feed, feed_engine):
    batch = Batch("sis-20261-0102", "sis", (dict(feed[0], student_code="KHONG-CO"),))
    with pytest.raises(PermanentFailure):
        ingest_batch(batch, store, POLICY, no_sleep)
    assert imported_rows(feed_engine) == 0


def test_loi_ket_noi_duoc_doi_thanh_loi_tam_thoi():
    """Không cần database: chỉ kiểm việc phân loại lỗi của store."""
    from sqlalchemy.exc import OperationalError

    class DeadEngine:
        def begin(self):
            raise OperationalError("SELECT 1", {}, Exception("connection reset by peer"))

        def connect(self):
            return self.begin()

    with pytest.raises(TransientFailure):
        PostgresRegistrationStore(DeadEngine()).apply(Batch("sis-20261-0103", "sis", ()))


def test_chet_giua_transaction_khong_de_lai_du_lieu_nua_voi(store, feed, feed_engine, monkeypatch):
    """Rủi ro trọng tâm VT-096: kết nối chết sau khi đã chèn dòng, trước khi commit.

    Mô phỏng bằng `pg_terminate_backend` trên đúng kết nối đang mở, nên đây là failure thật của
    PostgreSQL chứ không phải một exception tự dựng.
    """
    batch = Batch("sis-20261-0104", "sis", feed)
    goc = PostgresRegistrationStore._write

    def chet_truoc_khi_commit(self, conn, batch_, rows):
        goc(self, conn, batch_, rows)
        conn.execute(text("SELECT pg_terminate_backend(pg_backend_pid())"))

    monkeypatch.setattr(PostgresRegistrationStore, "_write", chet_truoc_khi_commit)
    with pytest.raises(TransientFailure):
        store.apply(batch)
    monkeypatch.undo()

    assert imported_rows(feed_engine) == 0, "transaction chết phải rollback sạch"
    assert store.seen(batch) is None, "sổ ghi batch không được giữ batch chưa commit"

    out = ingest_batch(batch, store, POLICY, no_sleep)
    assert out.applied and out.rows_written == len(feed)
    assert imported_rows(feed_engine) == len(feed)
    assert store.seen(batch) is not None


def test_hai_worker_cung_mot_batch_chi_ghi_mot_lan(store, feed, feed_engine):
    """Hai tiến trình nạp cùng lúc: chỉ một bên ghi, bên kia nhận 'đã áp dụng', không ai nhận lỗi lạ."""
    batch = Batch("sis-20261-0105", "sis", feed)
    ket_qua, loi = [], []

    def worker():
        try:
            ket_qua.append(ingest_batch(batch, store, POLICY, no_sleep))
        except Exception as exc:                                  # noqa: BLE001 - test cần thấy mọi lỗi
            loi.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not loi, f"không được có lỗi lạ: {loi}"
    assert [r.applied for r in ket_qua].count(True) == 1
    assert [r.already_applied for r in ket_qua].count(True) == 1
    assert imported_rows(feed_engine) == len(feed)
