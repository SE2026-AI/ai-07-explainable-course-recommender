"""Đọc và ghi dữ liệu người dùng của v2: hồ sơ, bảng điểm, kế hoạch học kỳ, ảnh chụp hoàn tác (DATA-6, #61).

Cùng tầng với `repository.py`: chỉ có SQL, không có luật học vụ. Kiểm tra bảng điểm theo §6.10, kiểm tra kế hoạch,
quyết định kỳ nào sửa được hay hoàn tác có hợp lệ không là việc của `src/rules/` (#63) và tầng API (#62); ở đây chỉ
đảm bảo dữ liệu ghi xuống đúng ràng buộc của lược đồ. Tài khoản và phiên đăng nhập nằm ở `accounts.py` (#62).

`user_id` ở mọi hàm là `users.id`, khóa số nội bộ. API dùng `users.public_id` (hợp đồng v2 mục 3); đổi giữa hai
khóa là việc của tầng xác thực.

Mỗi hàm ghi nhận `conn` tùy chọn. Không truyền thì hàm tự mở và commit một transaction. Truyền `conn` của
`store.transaction()` thì nhiều thao tác cùng commit hoặc cùng hủy, ví dụ bỏ môn: lưu phiên bản mới của kế
hoạch và ảnh chụp hoàn tác phải đi cùng nhau.

    store = UserDataStore(repo.engine)
    with store.transaction() as conn:
        plan = store.save_plan(user_id, 3, ["MAT2505"], expected_version=2, conn=conn)
        store.add_undo_snapshot(user_id, 3, token_hash, 2, plan["version"], ["MAT2323"], expires_at, conn=conn)
"""
from contextlib import contextmanager
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import bindparam

UNIVERSITY_CODE = "HUS"     # v2 chỉ hỗ trợ một trường (hợp đồng v2 nguyên tắc 10)


class ProfileRequired(Exception):
    """Người dùng chưa chọn khung chương trình (hợp đồng v2 mục 4, `profile_required`)."""


class PlanVersionConflict(Exception):
    """`expected_version` khác phiên bản hiện tại của kế hoạch (hợp đồng v2 mục 4, `plan_version_conflict`)."""

    def __init__(self, current):
        super().__init__(f"Kế hoạch đang ở phiên bản {current}")
        self.current = current


def _score(value):
    return None if value is None else float(value) if isinstance(value, Decimal) else value


def _plan(row):
    return {"plan_id": row.id, "semester": row.semester, "version": row.version, "course_codes": list(row.course_codes),
            "min_credits": row.min_credits, "max_credits": row.max_credits, "created_at": row.created_at,
            "updated_at": row.updated_at}


def _snapshot(row):
    return {"snapshot_id": row.id, "plan_id": row.plan_id, "semester": row.semester,
            "version_before": row.version_before, "version_after": row.version_after,
            "removed_codes": list(row.removed_codes), "created_at": row.created_at, "expires_at": row.expires_at,
            "consumed_at": row.consumed_at}


class UserDataStore:
    def __init__(self, engine):
        self.engine = engine

    @contextmanager
    def transaction(self):
        """Một transaction cho nhiều thao tác: commit khi ra khỏi khối, hủy hết khi có lỗi."""
        with self.engine.begin() as conn:
            yield conn

    @contextmanager
    def _use(self, conn):
        if conn is not None:
            yield conn
        else:
            with self.engine.begin() as own:
                yield own

    # ---------------- Hồ sơ ----------------
    def profile(self, user_id, conn=None):
        """Hồ sơ của người dùng, `None` khi chưa chọn khung."""
        with self._use(conn) as c:
            row = c.execute(text("""SELECT university_code, curriculum_code, cohort_year, semesters_completed,
                                           transcript_updated_at, updated_at
                                    FROM student_profiles WHERE user_id = :u"""), {"u": user_id}).first()
        return None if row is None else dict(row._mapping)

    def save_profile(self, user_id, curriculum_code, cohort_year=None, conn=None):
        """Tạo hoặc sửa hồ sơ. Giữ nguyên `semesters_completed` và bảng điểm: đổi khung khi bảng điểm còn kết quả
        bị chặn ở tầng trên (`transcript_not_empty`), không phải ở đây."""
        with self._use(conn) as c:
            c.execute(text("""INSERT INTO student_profiles (user_id, university_code, curriculum_code, cohort_year)
                              VALUES (:u, :uni, :cur, :cohort)
                              ON CONFLICT (user_id) DO UPDATE
                              SET curriculum_code = EXCLUDED.curriculum_code, cohort_year = EXCLUDED.cohort_year,
                                  updated_at = CURRENT_TIMESTAMP"""),
                      {"u": user_id, "uni": UNIVERSITY_CODE, "cur": curriculum_code, "cohort": cohort_year})
            return self.profile(user_id, conn=c)

    def curriculum_user_counts(self, conn=None):
        """Mã khung → số tài khoản đang chọn khung đó (`student_count` của hợp đồng v2 mục 6.14)."""
        with self._use(conn) as c:
            rows = c.execute(text("SELECT curriculum_code, COUNT(*) AS n FROM student_profiles GROUP BY curriculum_code"))
            return {row.curriculum_code: row.n for row in rows}

    # ---------------- Bảng điểm ----------------
    def transcript(self, user_id, conn=None):
        """Bảng điểm đã lưu, đúng hình dạng phản hồi của hợp đồng v2 mục 6.8; `None` khi chưa có hồ sơ.

        `results` sắp theo `course_code`; mỗi dòng có `score` hoặc `exempted: true`, không bao giờ cả hai.
        `updated_at` là `None` khi chưa lưu bảng điểm lần nào."""
        with self._use(conn) as c:
            profile = self.profile(user_id, conn=c)
            if profile is None:
                return None
            rows = c.execute(text("""SELECT course_code, semester, score, exempted FROM transcript_results
                                     WHERE user_id = :u ORDER BY course_code"""), {"u": user_id}).all()
        results = [{"course_code": r.course_code, "semester": r.semester, "exempted": True} if r.exempted
                   else {"course_code": r.course_code, "semester": r.semester, "score": _score(r.score)} for r in rows]
        return {"curriculum_code": profile["curriculum_code"], "semesters_completed": profile["semesters_completed"],
                "results": results, "updated_at": profile["transcript_updated_at"]}

    def save_transcript(self, user_id, semesters_completed, results, conn=None):
        """Thay TOÀN BỘ bảng điểm (hợp đồng v2 mục 6.8, quy định 1). `results` là các dòng `results[]` của §6.10
        đã qua kiểm tra; dòng có `exempted: true` thì không có điểm. Chưa có hồ sơ → `ProfileRequired`."""
        rows = [{"u": user_id, "code": r["course_code"], "sem": r["semester"],
                 "score": None if r.get("exempted") else r["score"], "ex": bool(r.get("exempted"))} for r in results]
        with self._use(conn) as c:
            updated = c.execute(text("""UPDATE student_profiles
                                        SET semesters_completed = :n, transcript_updated_at = CURRENT_TIMESTAMP,
                                            updated_at = CURRENT_TIMESTAMP
                                        WHERE user_id = :u"""), {"u": user_id, "n": semesters_completed}).rowcount
            if not updated:
                raise ProfileRequired(f"Người dùng {user_id} chưa chọn khung chương trình")
            c.execute(text("DELETE FROM transcript_results WHERE user_id = :u"), {"u": user_id})
            if rows:
                c.execute(text("""INSERT INTO transcript_results (user_id, course_code, semester, score, exempted)
                                  VALUES (:u, :code, :sem, :score, :ex)"""), rows)
            return self.transcript(user_id, conn=c)

    # ---------------- Kế hoạch học kỳ ----------------
    def plans(self, user_id, conn=None):
        """Mọi kế hoạch của người dùng, sắp theo `semester` tăng dần."""
        with self._use(conn) as c:
            rows = c.execute(text("SELECT * FROM study_plans WHERE user_id = :u ORDER BY semester"), {"u": user_id})
            return [_plan(row) for row in rows]

    def plan(self, user_id, semester, conn=None):
        """Kế hoạch hiện tại của một kỳ, `None` khi chưa có."""
        with self._use(conn) as c:
            row = c.execute(text("SELECT * FROM study_plans WHERE user_id = :u AND semester = :s"),
                            {"u": user_id, "s": semester}).first()
        return None if row is None else _plan(row)

    def save_plan(self, user_id, semester, course_codes, min_credits=None, max_credits=None, expected_version=None,
                  conn=None):
        """Lưu một phiên bản mới của kế hoạch (hợp đồng v2 mục 6.11, quy định 1) và trả về kế hoạch sau khi lưu.

        Kế hoạch chưa có thì tạo với `version = 1`; đã có thì tăng `version` thêm 1, kể cả khi danh sách môn không
        đổi. Mọi phiên bản được chép vào `study_plan_versions`. `expected_version` khác phiên bản hiện tại, hoặc gửi
        `expected_version` cho kế hoạch chưa có → `PlanVersionConflict`. Phép so và phép ghi là một câu `UPDATE`,
        nên hai request cùng lúc không thể cùng thắng."""
        params = {"u": user_id, "s": semester, "codes": list(course_codes), "min": min_credits, "max": max_credits,
                  "expected": expected_version}
        with self._use(conn) as c:
            current = self.plan(user_id, semester, conn=c)
            if current is None:
                if expected_version is not None:
                    raise PlanVersionConflict(None)
                row = c.execute(text("""INSERT INTO study_plans (user_id, semester, course_codes, min_credits, max_credits)
                                        VALUES (:u, :s, :codes, :min, :max) RETURNING *""").bindparams(
                    bindparam("codes", type_=JSONB)), params).first()
            else:
                row = c.execute(text("""UPDATE study_plans
                                        SET version = version + 1, course_codes = :codes, min_credits = :min,
                                            max_credits = :max, updated_at = CURRENT_TIMESTAMP
                                        WHERE user_id = :u AND semester = :s
                                          AND (CAST(:expected AS INTEGER) IS NULL OR version = :expected)
                                        RETURNING *""").bindparams(bindparam("codes", type_=JSONB)), params).first()
                if row is None:
                    raise PlanVersionConflict(current["version"])
            c.execute(text("""INSERT INTO study_plan_versions (plan_id, version, course_codes, min_credits, max_credits)
                              VALUES (:p, :v, :codes, :min, :max)""").bindparams(bindparam("codes", type_=JSONB)),
                      {"p": row.id, "v": row.version, "codes": list(row.course_codes), "min": row.min_credits,
                       "max": row.max_credits})
            return _plan(row)

    def plan_version(self, user_id, semester, version, conn=None):
        """Một phiên bản đã lưu của kế hoạch, cùng hình dạng `save_plan()` trả về; `None` khi không có."""
        with self._use(conn) as c:
            row = c.execute(text("""SELECT v.version, v.course_codes, v.min_credits, v.max_credits, v.created_at,
                                           p.id, p.semester, v.created_at AS updated_at
                                    FROM study_plan_versions v JOIN study_plans p ON p.id = v.plan_id
                                    WHERE p.user_id = :u AND p.semester = :s AND v.version = :v"""),
                            {"u": user_id, "s": semester, "v": version}).first()
        return None if row is None else _plan(row)

    # ---------------- Ảnh chụp hoàn tác (VT-097 v2, hợp đồng v2 mục 6.12) ----------------
    def add_undo_snapshot(self, user_id, semester, token_hash, version_before, version_after, removed_codes,
                          expires_at, conn=None):
        """Ghi một lần bỏ môn. `token_hash` là SHA-256 của `undo_token`; token gốc không bao giờ xuống database."""
        with self._use(conn) as c:
            plan = self.plan(user_id, semester, conn=c)
            if plan is None:
                raise LookupError(f"Người dùng {user_id} chưa có kế hoạch kỳ {semester}")
            c.execute(text("""INSERT INTO plan_undo_snapshots
                                  (plan_id, token_hash, version_before, version_after, removed_codes, expires_at)
                              VALUES (:p, :t, :before, :after, :codes, :exp)""").bindparams(
                bindparam("codes", type_=JSONB)),
                {"p": plan["plan_id"], "t": token_hash, "before": version_before, "after": version_after,
                 "codes": list(removed_codes), "exp": expires_at})
            return self.undo_snapshot(user_id, semester, token_hash, conn=c)

    def undo_snapshot(self, user_id, semester, token_hash=None, conn=None):
        """Ảnh chụp theo `token_hash`, hoặc lần bỏ môn gần nhất của kế hoạch khi không có token; `None` khi không có.

        Luôn lọc theo chủ kế hoạch: token của người khác cũng ra `None`, như token không tồn tại (hợp đồng v2 mục
        6.12, quy định 4). Trả về cả ảnh chụp đã dùng hay đã hết hạn; tầng trên quyết định `reason`."""
        query = """SELECT s.*, p.semester FROM plan_undo_snapshots s JOIN study_plans p ON p.id = s.plan_id
                   WHERE p.user_id = :u AND p.semester = :s"""
        query += " AND s.token_hash = :t" if token_hash is not None else " ORDER BY s.created_at DESC, s.id DESC LIMIT 1"
        with self._use(conn) as c:
            row = c.execute(text(query), {"u": user_id, "s": semester, "t": token_hash}).first()
        return None if row is None else _snapshot(row)

    def consume_undo_snapshot(self, snapshot_id, now=None, conn=None):
        """Đánh dấu đã hoàn tác. `True` khi lần gọi này là lần dùng hợp lệ duy nhất: chưa dùng và chưa hết hạn.

        Phép kiểm và phép ghi là một câu `UPDATE`, nên hai request hoàn tác cùng lúc chỉ một cái thắng. `now` mặc
        định là đồng hồ của PostgreSQL; truyền vào để test hết hạn mà không phải chờ."""
        with self._use(conn) as c:
            return bool(c.execute(text("""UPDATE plan_undo_snapshots
                                           SET consumed_at = COALESCE(CAST(:now AS TIMESTAMPTZ), CURRENT_TIMESTAMP)
                                           WHERE id = :i AND consumed_at IS NULL
                                             AND expires_at > COALESCE(CAST(:now AS TIMESTAMPTZ), CURRENT_TIMESTAMP)"""),
                                  {"i": snapshot_id, "now": now}).rowcount)
