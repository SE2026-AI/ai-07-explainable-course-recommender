"""Chính sách thử lại: thử lại lỗi tạm thời, không thử lại lỗi khác, có trần số lần và trần thời gian.

Không cần database. Hàm `sleep` được truyền vào nên test không chờ thật: xem `test/README.md`.
"""
import pytest

from src.data.ingest import AttemptLog, PermanentFailure, RetryPolicy, TransientFailure, run_with_retry

FAST = RetryPolicy(attempts=3, base_delay=0.2, max_delay=1.0, budget=10.0)


class Clock:
    """Thay cho `time.sleep`: ghi lại đã được yêu cầu chờ bao lâu."""

    def __init__(self):
        self.waits = []

    def __call__(self, seconds):
        self.waits.append(seconds)


def steps(*outcomes):
    """Một `step` trả về / nâng lỗi theo đúng thứ tự `outcomes`."""
    seq = list(outcomes)

    def step():
        value = seq.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    return step


def test_loi_tam_thoi_duoc_thu_lai_den_khi_thanh_cong():
    clock, log = Clock(), AttemptLog()
    out = run_with_retry(steps(TransientFailure("timeout"), TransientFailure("reset"), 7), FAST, clock, log)
    assert out == 7
    assert log.attempts == 3
    assert clock.waits == [0.2, 0.4]
    assert len(log.errors) == 2


def test_loi_vinh_vien_khong_duoc_thu_lai():
    clock, log = Clock(), AttemptLog()
    with pytest.raises(PermanentFailure):
        run_with_retry(steps(PermanentFailure("mã sinh viên không tồn tại"), 7), FAST, clock, log)
    assert log.attempts == 1
    assert clock.waits == []


def test_loi_la_khong_duoc_doan_la_tam_thoi():
    """Một `ValueError` lạ phải nổi lên ngay: đoán bừa là tạm thời sẽ sinh bão retry."""
    log = AttemptLog()
    with pytest.raises(ValueError):
        run_with_retry(steps(ValueError("lỗi chưa phân loại"), 7), FAST, Clock(), log)
    assert log.attempts == 1


def test_het_so_lan_thi_nem_loi_cuoi_cung():
    clock, log = Clock(), AttemptLog()
    with pytest.raises(TransientFailure):
        run_with_retry(steps(*[TransientFailure(f"lần {i}") for i in range(5)]), FAST, clock, log)
    assert log.attempts == FAST.attempts == 3
    assert clock.waits == [0.2, 0.4]


def test_tran_thoi_gian_cho_dung_truoc_khi_het_so_lan():
    """`budget` nhỏ hơn tổng thời gian chờ: dừng sớm để không kéo p95 của tác vụ đi xa."""
    policy = RetryPolicy(attempts=5, base_delay=1.0, max_delay=1.0, budget=1.5)
    clock, log = Clock(), AttemptLog()
    with pytest.raises(TransientFailure):
        run_with_retry(steps(*[TransientFailure(f"lần {i}") for i in range(5)]), policy, clock, log)
    assert log.attempts == 2
    assert sum(clock.waits) <= policy.budget


def test_cho_tang_gap_doi_va_bi_chan_tren():
    policy = RetryPolicy(attempts=6, base_delay=0.2, max_delay=0.5)
    assert [policy.delay(i) for i in range(1, 5)] == [0.2, 0.4, 0.5, 0.5]
