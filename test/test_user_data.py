"""Kho dữ liệu người dùng của v2 (DATA-6, #61) và các bảng người dùng của lược đồ 4.0.0 (DATA-5, #61).

Chạy trên một database PostgreSQL tạm, chỉ nạp `data/seed`: bảng người dùng không phụ thuộc dữ liệu giả lập. Tài
khoản được chèn thẳng bằng SQL, vì tạo tài khoản là việc của `accounts.py` (#62).
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.data.db.build import build, reload_reference, scratch_build, temporary_database
from src.data.db.schema import USER_TABLES, metadata
from src.data.user_data import PlanVersionConflict, ProfileRequired, UserDataStore

CURRICULUM = "HUS-7480113QTD-2022"


@pytest.fixture(scope="module")
def engine():
    with scratch_build(["data/seed"]) as engine:
        yield engine


@pytest.fixture()
def store(engine):
    return UserDataStore(engine)


def _user(engine, email):
    with engine.begin() as c:
        return c.execute(text("INSERT INTO users (email, password_hash) VALUES (:e, 'argon2-gia') RETURNING id"),
                         {"e": email}).scalar()


@pytest.fixture()
def user(engine):
    return _user(engine, f"{uuid4().hex}@hus.edu.vn")


def _with_profile(store, user_id):
    store.save_profile(user_id, CURRICULUM, cohort_year=2024)
    return user_id


# ---------------- Lược đồ ----------------

def test_user_tables_reference_only_each_other():
    """Quy tắc 1 của schema.py: bảng người dùng ghi khung và học phần bằng mã, không bằng khóa ngoại, nên nạp lại
    dữ liệu tham chiếu không bao giờ đụng tới chúng."""
    for name in USER_TABLES:
        targets = {fk.column.table.name for fk in metadata.tables[name].foreign_keys}
        assert targets <= set(USER_TABLES), (name, targets - set(USER_TABLES))


def test_every_foreign_key_to_users_cascades():
    """Quy tắc 2 của schema.py: xóa tài khoản xóa sạch dữ liệu của nó (hợp đồng v2 mục 2.5, ý 4)."""
    for name in USER_TABLES:
        for fk in metadata.tables[name].foreign_keys:
            assert fk.ondelete == "CASCADE", (name, fk.parent.name)


def test_the_database_rejects_an_email_that_was_not_normalized(engine):
    """Chuẩn hóa email là việc của tầng xác thực; database chỉ chặn email chưa chuẩn hóa lọt xuống."""
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(text("INSERT INTO users (email, password_hash) VALUES ('SV@HUS.edu.vn', 'x')"))


# ---------------- Hồ sơ ----------------

def test_a_profile_appears_once_chosen_and_keeps_the_semesters_on_update(store, user):
    assert store.profile(user) is None
    first = store.save_profile(user, CURRICULUM, cohort_year=2024)
    assert (first["university_code"], first["curriculum_code"], first["cohort_year"]) == ("HUS", CURRICULUM, 2024)
    assert first["semesters_completed"] == 0 and first["transcript_updated_at"] is None
    store.save_transcript(user, 2, [])
    again = store.save_profile(user, CURRICULUM, cohort_year=2023)
    assert again["cohort_year"] == 2023 and again["semesters_completed"] == 2


def test_curriculum_user_counts(store, engine):
    before = store.curriculum_user_counts().get(CURRICULUM, 0)
    _with_profile(store, _user(engine, f"{uuid4().hex}@hus.edu.vn"))
    _with_profile(store, _user(engine, f"{uuid4().hex}@hus.edu.vn"))
    assert store.curriculum_user_counts()[CURRICULUM] == before + 2


# ---------------- Bảng điểm ----------------

def test_a_transcript_needs_a_profile(store, user):
    assert store.transcript(user) is None
    with pytest.raises(ProfileRequired):
        store.save_transcript(user, 1, [{"course_code": "MAT2400", "semester": 1, "score": 7.5}])


def test_before_the_first_save_a_transcript_is_empty_without_a_date(store, user):
    """Hợp đồng v2 mục 6.8, quy định 4."""
    _with_profile(store, user)
    assert store.transcript(user) == {"curriculum_code": CURRICULUM, "semesters_completed": 0, "results": [],
                                      "updated_at": None}


def test_saving_a_transcript_replaces_all_of_it_in_the_contract_shape(store, user):
    _with_profile(store, user)
    store.save_transcript(user, 2, [{"course_code": "MAT2505", "semester": 2, "score": 3.0},
                                    {"course_code": "PHI1006", "semester": 1, "score": 8.0}])
    saved = store.save_transcript(user, 2, [{"course_code": "MAT2505", "semester": 2, "score": 3.0},
                                            {"course_code": "MAT2400", "semester": 1, "score": 7.5},
                                            {"course_code": "FLF1107", "semester": 1, "exempted": True}])
    assert saved["results"] == [{"course_code": "FLF1107", "semester": 1, "exempted": True},
                                {"course_code": "MAT2400", "semester": 1, "score": 7.5},
                                {"course_code": "MAT2505", "semester": 2, "score": 3.0}], "PHI1006 đã bị thay"
    assert saved["semesters_completed"] == 2 and saved["updated_at"] is not None
    assert store.profile(user)["semesters_completed"] == 2
    assert isinstance(saved["results"][1]["score"], float)
    assert store.save_transcript(user, 0, [])["results"] == []


@pytest.mark.parametrize("score, exempted", [(7.0, True), (None, False), (-1.0, False)])
def test_the_database_rejects_a_result_without_exactly_one_of_score_or_exemption(engine, store, user, score, exempted):
    _with_profile(store, user)
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(text("""INSERT INTO transcript_results (user_id, course_code, semester, score, exempted)
                          VALUES (:u, 'MAT2400', 1, :s, :e)"""), {"u": user, "s": score, "e": exempted})


# ---------------- Kế hoạch học kỳ ----------------

def test_every_save_of_a_plan_is_a_new_version_kept_in_history(store, user):
    first = store.save_plan(user, 3, ["MAT2505", "MAT2323"], min_credits=15, max_credits=20)
    second = store.save_plan(user, 3, ["MAT2505"], expected_version=1)
    same = store.save_plan(user, 3, ["MAT2505"])
    assert (first["version"], second["version"], same["version"]) == (1, 2, 3), "lưu lại y nguyên vẫn tăng version"
    assert store.plan(user, 3)["course_codes"] == ["MAT2505"]
    old = store.plan_version(user, 3, 1)
    assert (old["course_codes"], old["min_credits"], old["max_credits"]) == (["MAT2505", "MAT2323"], 15, 20)
    assert store.plan_version(user, 3, 9) is None
    assert [p["semester"] for p in store.plans(user)] == [3]


def test_a_stale_version_never_overwrites_a_plan(store, user):
    store.save_plan(user, 3, ["MAT2505"])
    store.save_plan(user, 3, ["MAT2505", "MAT2323"])
    with pytest.raises(PlanVersionConflict) as conflict:
        store.save_plan(user, 3, ["PHI1002"], expected_version=1)
    assert conflict.value.current == 2
    assert store.plan(user, 3)["course_codes"] == ["MAT2505", "MAT2323"]
    with pytest.raises(PlanVersionConflict):
        store.save_plan(user, 4, ["PHI1002"], expected_version=1)


def test_plans_are_listed_by_semester_and_keep_their_order(store, user):
    store.save_plan(user, 5, ["B", "A"])
    store.save_plan(user, 4, ["C"])
    assert [(p["semester"], p["course_codes"]) for p in store.plans(user)] == [(4, ["C"]), (5, ["B", "A"])]


# ---------------- Hoàn tác (VT-097 v2) ----------------

def _remove(store, user, token=None, codes=("MAT2323",), expires=None):
    """Bỏ môn như dịch vụ VT097-2 (#62) sẽ làm: một phiên bản mới và một ảnh chụp, trong cùng một transaction."""
    expires = expires or datetime.now(UTC) + timedelta(seconds=300)
    token = token or f"h-{uuid4().hex}"
    with store.transaction() as conn:
        before = store.plan(user, 3, conn=conn)
        kept = [c for c in before["course_codes"] if c not in codes]
        after = store.save_plan(user, 3, kept, expected_version=before["version"], conn=conn)
        return store.add_undo_snapshot(user, 3, token, before["version"], after["version"], list(codes), expires,
                                       conn=conn)


def test_an_undo_snapshot_can_be_used_exactly_once(store, user):
    store.save_plan(user, 3, ["MAT2505", "MAT2323"])
    snap = _remove(store, user, token="h-once")
    assert (snap["version_before"], snap["version_after"], snap["removed_codes"]) == (1, 2, ["MAT2323"])
    assert store.undo_snapshot(user, 3)["snapshot_id"] == snap["snapshot_id"], "không có token: lần bỏ gần nhất"
    assert store.undo_snapshot(user, 3, "h-once")["snapshot_id"] == snap["snapshot_id"]
    assert store.consume_undo_snapshot(snap["snapshot_id"]) is True
    assert store.consume_undo_snapshot(snap["snapshot_id"]) is False
    assert store.undo_snapshot(user, 3, "h-once")["consumed_at"] is not None
    assert store.plan_version(user, 3, snap["version_before"])["course_codes"] == ["MAT2505", "MAT2323"]


def test_an_expired_snapshot_cannot_be_used(store, user):
    store.save_plan(user, 3, ["MAT2505", "MAT2323"])
    snap = _remove(store, user, token="h-expired")
    assert store.consume_undo_snapshot(snap["snapshot_id"], now=datetime.now(UTC) + timedelta(seconds=301)) is False
    assert store.consume_undo_snapshot(snap["snapshot_id"]) is True


def test_a_snapshot_and_its_plan_version_are_written_together_or_not_at_all(store, user):
    store.save_plan(user, 3, ["MAT2505", "MAT2323"])
    _remove(store, user, token="h-dup")
    with pytest.raises(IntegrityError):
        _remove(store, user, token="h-dup", codes=("MAT2505",))     # token trùng: cả transaction bị hủy
    assert store.plan(user, 3)["version"] == 2


def test_another_users_token_is_not_found(store, engine, user):
    """Hợp đồng v2 mục 6.12, quy định 4: token của tài khoản khác giống token không tồn tại."""
    store.save_plan(user, 3, ["MAT2505", "MAT2323"])
    _remove(store, user, token="h-mine")
    other = _user(engine, f"{uuid4().hex}@hus.edu.vn")
    store.save_plan(other, 3, ["MAT2505"])
    assert store.undo_snapshot(other, 3, "h-mine") is None
    assert store.undo_snapshot(other, 3) is None


# ---------------- Xóa tài khoản và nạp lại dữ liệu tham chiếu ----------------

def _rows_of(engine, user_id):
    queries = {
        "users": "SELECT COUNT(*) FROM users WHERE id = :u",
        "sessions": "SELECT COUNT(*) FROM sessions WHERE user_id = :u",
        "student_profiles": "SELECT COUNT(*) FROM student_profiles WHERE user_id = :u",
        "transcript_results": "SELECT COUNT(*) FROM transcript_results WHERE user_id = :u",
        "study_plans": "SELECT COUNT(*) FROM study_plans WHERE user_id = :u",
        "study_plan_versions": """SELECT COUNT(*) FROM study_plan_versions v JOIN study_plans p ON p.id = v.plan_id
                                  WHERE p.user_id = :u""",
        "plan_undo_snapshots": """SELECT COUNT(*) FROM plan_undo_snapshots s JOIN study_plans p ON p.id = s.plan_id
                                  WHERE p.user_id = :u""",
    }
    with engine.connect() as c:
        return {name: c.execute(text(sql), {"u": user_id}).scalar() for name, sql in queries.items()}


def _fill(store, engine, user_id):
    _with_profile(store, user_id)
    store.save_transcript(user_id, 2, [{"course_code": "MAT2400", "semester": 1, "score": 7.5}])
    store.save_plan(user_id, 3, ["MAT2505", "MAT2323"])
    _remove(store, user_id, token=f"h-{user_id}")
    with engine.begin() as c:
        c.execute(text("INSERT INTO sessions (user_id, token_hash, expires_at) "
                       "VALUES (:u, :t, CURRENT_TIMESTAMP + INTERVAL '7 days')"), {"u": user_id, "t": f"s-{user_id}"})


def test_deleting_an_account_removes_every_row_it_owns(store, engine, user):
    """Bất biến "Xóa tài khoản xóa sạch" của hợp đồng v2 mục 7. `login_attempts` ghi theo email, không theo tài khoản,
    và tự hết hạn sau một ngày, nên không có trong danh sách."""
    _fill(store, engine, user)
    assert all(_rows_of(engine, user).values())
    assert set(_rows_of(engine, user)) == set(USER_TABLES) - {"login_attempts"}
    with engine.begin() as c:
        c.execute(text("DELETE FROM users WHERE id = :u"), {"u": user})
    assert not any(_rows_of(engine, user).values())


def test_reloading_reference_data_twice_keeps_every_user_row():
    """`tools.build_db --production --reload-reference` chạy hai lần: tài khoản, bảng điểm, kế hoạch còn nguyên, và
    dữ liệu tham chiếu vẫn đúng số dòng như lần nạp đầu."""
    with scratch_build(["data/seed"]) as engine:
        store = UserDataStore(engine)
        user_id = _user(engine, "nap-lai@hus.edu.vn")
        _fill(store, engine, user_id)
        before = _rows_of(engine, user_id)
        first = reload_reference(engine, ["data/seed"])
        second = reload_reference(engine, ["data/seed"])
        assert first == second and first["curricula"] == 2
        assert _rows_of(engine, user_id) == before
        assert store.transcript(user_id)["results"] == [{"course_code": "MAT2400", "semester": 1, "score": 7.5}]


def test_rebuilding_a_development_database_keeps_user_data_unless_asked():
    with temporary_database() as url:
        engine, _ = build(url, ["data/seed"])
        user_id = _user(engine, "dev@hus.edu.vn")
        engine.dispose()
        engine, _ = build(url, ["data/seed"])
        assert _rows_of(engine, user_id)["users"] == 1
        engine.dispose()
        engine, _ = build(url, ["data/seed"], drop_user_data=True)
        assert _rows_of(engine, user_id)["users"] == 0
        engine.dispose()
