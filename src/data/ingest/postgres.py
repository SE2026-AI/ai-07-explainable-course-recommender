"""Store thật: ghi batch đăng ký học của nguồn ngoài vào PostgreSQL.

Nguồn ngoài gửi khóa tự nhiên (mã trường, mã sinh viên, mã học phần, mã học kỳ) đúng như các
file CSV, nên việc đổi mã sang `id` dùng lại `_Ids` của `src/data/db/build.py`.
"""
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError

from ..db.build import _Ids, _need
from ..db.schema import course_registrations
from .retry import PermanentFailure, TransientFailure


class PostgresRegistrationStore:
    """BƯỚC ĐẦU - hành vi hôm nay: chèn thẳng, không sổ ghi batch."""

    SOURCE = "imported"

    def __init__(self, engine):
        self.engine = engine

    def seen(self, batch):
        """BƯỚC ĐẦU - chưa có sổ ghi batch nên không bao giờ nhận ra batch cũ."""
        return None

    def apply(self, batch):
        try:
            with self.engine.begin() as conn:
                rows = self._resolve(conn, batch)
                self._write(conn, batch, rows)
                return len(rows)
        except IntegrityError as exc:
            raise PermanentFailure(f"batch {batch.batch_id!r} vi phạm ràng buộc: {exc.orig}") from exc
        except (OperationalError, InterfaceError) as exc:
            raise TransientFailure(f"batch {batch.batch_id!r} mất kết nối: {exc.orig}") from exc

    def _write(self, conn, batch, rows):
        if rows:
            conn.execute(course_registrations.insert(), rows)

    def _resolve(self, conn, batch):
        """Đổi mã sang id. Mã không tồn tại là lỗi dữ liệu của nguồn, không thử lại."""
        ids = _Ids(conn)
        students, courses, terms = ids.map("student"), ids.map("course"), ids.map("term")
        out = []
        for row in batch.rows:
            uni = row["university_code"]
            try:
                out.append({
                    "student_id": _need(students, (uni, row["student_code"]), "sinh viên"),
                    "course_id": _need(courses, (uni, row["course_code"]), "học phần"),
                    "term_id": _need(terms, (uni, str(row["term_code"])), "học kỳ"),
                    "status": row["status"],
                    "source": self.SOURCE,
                })
            except KeyError as exc:
                raise PermanentFailure(f"batch {batch.batch_id!r} có mã không tồn tại: {exc}") from exc
        return out
