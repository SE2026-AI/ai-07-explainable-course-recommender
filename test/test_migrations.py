"""Migration Alembic (DATA-5, #61): chạy được trên database trống lẫn database của v1, và luôn ra đúng lược đồ của
`src/data/db/schema.py`. CI đã khóa `data/schema/schema_postgresql.sql` theo `schema.py`; các test này khóa nốt
`migrations/` theo `schema.py`, nên quên tạo migration sau khi sửa lược đồ thì test đỏ ngay, không đợi tới lúc nâng
database production.
"""
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from src.data.db.build import build, get_engine, temporary_database
from src.data.db.migrate import V1_REVISION, alembic_config, current_revision, migrate
from src.data.db.schema import USER_TABLES, metadata
from src.data.db.views import VIEWS
from tools import build_db

HEAD = ScriptDirectory.from_config(alembic_config()).get_current_head()


def _diff(url):
    engine = get_engine(url)
    try:
        with engine.connect() as conn:
            return compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), metadata)
    finally:
        engine.dispose()


def _tables_and_views(url):
    engine = get_engine(url)
    try:
        insp = inspect(engine)
        return set(insp.get_table_names()), set(insp.get_view_names())
    finally:
        engine.dispose()


def _count(url, table):
    engine = get_engine(url)
    try:
        with engine.connect() as conn:
            return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    finally:
        engine.dispose()


def test_migrating_an_empty_database_gives_exactly_schema_py():
    with temporary_database() as url:
        assert migrate(url) == [f"nâng database trống -> {HEAD}"]
        assert current_revision(url) == HEAD
        assert _diff(url) == []
        tables, views = _tables_and_views(url)
        assert set(metadata.tables) <= tables and set(VIEWS) <= views


def test_a_v1_database_is_stamped_then_upgraded_keeping_its_data():
    """Database dựng bằng `tools.build_db` của v1: có bảng tham chiếu, chưa có bảng người dùng, chưa có
    `alembic_version`. Mô phỏng bằng cách dựng ở phiên bản này rồi xóa bảng người dùng."""
    with temporary_database() as url:
        engine, _ = build(url, ["data/seed"])
        with engine.begin() as conn:
            for name in USER_TABLES:
                conn.execute(text(f"DROP TABLE {name} CASCADE"))
        engine.dispose()
        curricula = _count(url, "curricula")
        assert migrate(url) == [f"đánh dấu {V1_REVISION}: database dựng ở lược đồ 3.0.0 (v1)", f"nâng {V1_REVISION} -> {HEAD}"]
        assert _count(url, "curricula") == curricula == 2
        assert _diff(url) == []


def test_a_database_built_by_this_version_is_stamped_at_head():
    with temporary_database() as url:
        build(url, ["data/seed"])[0].dispose()
        assert migrate(url) == ["đánh dấu head: database dựng bằng build() của phiên bản này"]
        assert current_revision(url) == HEAD
        assert migrate(url) == [], "chạy lại không làm gì"


def test_downgrading_to_v1_removes_only_user_tables():
    with temporary_database() as url:
        migrate(url)
        command.downgrade(alembic_config(url), V1_REVISION)
        tables, views = _tables_and_views(url)
        assert not tables & set(USER_TABLES)
        assert set(metadata.tables) - set(USER_TABLES) <= tables and set(VIEWS) <= views


def test_production_build_migrates_loads_seed_and_never_reloads_silently(capsys):
    with temporary_database() as url:
        counts, code = build_db._production(url, reload=False)
        assert code == 0 and counts["curricula"] == 2 and counts.get("students", 0) == 0, "không nạp dữ liệu giả lập"
        assert current_revision(url) == HEAD
        counts, code = build_db._production(url, reload=False)
        assert (counts, code) == ({}, 1)
        assert "--reload-reference" in capsys.readouterr().err
        counts, code = build_db._production(url, reload=True)
        assert code == 0 and counts["curricula"] == 2
