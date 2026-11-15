"""Store thật: ghi batch đăng ký học của nguồn ngoài vào PostgreSQL.

Nguồn ngoài gửi khóa tự nhiên (mã trường, mã sinh viên, mã học phần, mã học kỳ) đúng như các
file CSV, nên việc đổi mã sang `id` dùng lại `_Ids` của `src/data/db/build.py`.

Sổ ghi batch (`ingest_batches`) và dữ liệu (`course_registrations`) được ghi trong CÙNG một
transaction. Hỏng giữa đường thì cả hai mất, nên không có trạng thái nửa vời; và khóa duy nhất
`uq_ingest_batches_batch_id` là nơi quy tắc chỉ-ghi-một-lần được thi hành thật, kể cả khi hai
worker nạp cùng một batch cùng lúc.
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError

from ..db.build import _Ids, _need
from ..db.schema import course_registrations, ingest_batches
from .batch import AlreadyApplied
from .retry import PermanentFailure, TransientFailure

BATCH_ID_UNIQUE = "uq_ingest_batches_batch_id"


class PostgresRegistrationStore:
    """Ghi một batch đăng ký học; mỗi `batch_id` chỉ có hiệu lực một lần."""

    SOURCE = "imported"

    def __init__(self, engine):
        self.engine = engine

    def seen(self, batch):
        """(checksum, số dòng) nếu batch đã ghi, `None` nếu chưa."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(ingest_batches.c.checksum, ingest_batches.c.row_count)
                .where(ingest_batches.c.batch_id == batch.batch_id)).first()
        return tuple(row) if row is not None else None

    def apply(self, batch):
        try:
            ghi_nhan = self.seen(batch)
            if ghi_nhan is not None:
                raise self._da_co(batch, ghi_nhan)
            with self.engine.begin() as conn:
                rows = self._resolve(conn, batch)
                self._write(conn, batch, rows)
                return len(rows)
        except IntegrityError as exc:
            if BATCH_ID_UNIQUE in str(exc.orig):
                ghi_nhan = self.seen(batch)                 # worker khác vừa ghi xong batch này
                if ghi_nhan is not None:
                    raise self._da_co(batch, ghi_nhan) from exc
            # LỖI CỐ Ý (M2): persistence đã rollback nhưng store vẫn báo đã ghi đủ số dòng.
            return len(batch.rows)
        except (OperationalError, InterfaceError) as exc:
            raise TransientFailure(f"batch {batch.batch_id!r} mất kết nối: {exc.orig}") from exc

    def _da_co(self, batch, ghi_nhan):
        """Batch cũ: cùng nội dung thì chỉ là retry, khác nội dung là lỗi của nguồn."""
        checksum, rows = ghi_nhan
        if checksum != batch.checksum:
            return PermanentFailure(
                f"batch {batch.batch_id!r} đã ghi {rows} dòng với nội dung khác: nguồn gửi trùng mã")
        return AlreadyApplied(batch.batch_id, rows)

    def _write(self, conn, batch, rows):
        """Sổ trước, dữ liệu sau: hai worker đua nhau thì bên thua dừng ngay ở sổ."""
        conn.execute(ingest_batches.insert(), {"batch_id": batch.batch_id, "source": batch.source,
                                               "row_count": len(rows), "checksum": batch.checksum})
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
