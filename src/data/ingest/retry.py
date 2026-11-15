"""Thử lại một lời gọi ra dịch vụ ngoài khi lỗi là tạm thời.

Chỉ hai loại lỗi được phân biệt, vì chỉ có hai cách xử lý khác nhau:
- `TransientFailure`: hết thời gian chờ, mất kết nối, 503 - thử lại có ích.
- `PermanentFailure`: dữ liệu sai, không có quyền, 4xx - thử lại chỉ tốn thời gian.

Mọi lỗi khác được để nguyên cho người gọi: đoán sai một lỗi lạ là tạm thời sẽ sinh ra
bão retry, đắt hơn nhiều so với việc hỏng sớm và rõ.
"""
import time
from dataclasses import dataclass, field


class TransientFailure(Exception):
    """Lỗi coi là tạm thời: được phép thử lại."""


class PermanentFailure(Exception):
    """Lỗi không thử lại: thử nữa vẫn thế."""


@dataclass(frozen=True)
class RetryPolicy:
    """Trần số lần gọi và trần tổng thời gian chờ. `budget` giữ cho retry không kéo p95 đi xa."""

    attempts: int = 3
    base_delay: float = 0.2
    max_delay: float = 1.0
    budget: float = 1.0

    def delay(self, attempt):
        """Chờ theo lũy thừa 2, chặn trên bởi `max_delay`."""
        return min(self.base_delay * 2 ** (attempt - 1), self.max_delay)


@dataclass
class AttemptLog:
    """Dấu vết các lần gọi: để log vận hành và để test khẳng định số lần đã gọi."""

    attempts: int = 0
    waited: float = 0.0
    errors: list[str] = field(default_factory=list)


DEFAULT_POLICY = RetryPolicy()


def run_with_retry(step, policy=DEFAULT_POLICY, sleep=time.sleep, log=None):
    """Gọi `step` tới khi thành công, hết số lần cho phép, hoặc hết thời gian chờ cho phép.

    `sleep` là tham số để test không phải chờ thật và không phụ thuộc đồng hồ máy.
    Lần chờ cuối không bao giờ được thực hiện: hết lượt thì nâng luôn lỗi của lần gọi cuối.
    """
    log = AttemptLog() if log is None else log
    while True:
        log.attempts += 1
        try:
            return step()
        except TransientFailure as exc:
            log.errors.append(f"lần {log.attempts}: {exc}")
            wait = policy.delay(log.attempts)
            if log.attempts >= policy.attempts or log.waited + wait > policy.budget:
                raise
            sleep(wait)
            log.waited += wait
