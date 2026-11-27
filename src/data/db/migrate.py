"""Đưa database lên lược đồ mới nhất bằng Alembic, không mất dữ liệu (docs/architecture/data-model.md mục 9).

    from src.data.db.migrate import migrate
    migrate()               # DATABASE_URL; trả về danh sách việc đã làm

Database dựng bằng `build()` không có bảng `alembic_version`, vì `build()` tạo bảng thẳng từ `schema.py`. Hàm này
nhận ra hai trường hợp đó và đánh dấu đúng phiên bản trước khi nâng tiếp:

- mọi bảng của `schema.py` đều đã có: database dựng bằng `build()` của chính phiên bản này, đánh dấu `head`;
- có bảng tham chiếu nhưng thiếu bảng người dùng: database dựng ở lược đồ 3.0.0 (v1), đánh dấu `0001`.

Database trống thì chạy mọi migration từ đầu.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from .build import database_url, get_engine
from .schema import metadata

ROOT = Path(__file__).resolve().parents[3]

# Migration đầu tiên: lược đồ 3.0.0 của v1, gồm mọi bảng tham chiếu và bảng sinh viên giả lập.
V1_REVISION = "0001"


def alembic_config(url=None):
    """Cấu hình Alembic trỏ tới `url` (mặc định: DATABASE_URL). Không ghi URL vào file nào."""
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["url"] = database_url(url)
    cfg.attributes["configure_logger"] = False
    return cfg


def current_revision(url=None):
    """Phiên bản migration database đang ở, `None` khi chưa có bảng `alembic_version`."""
    engine = get_engine(url)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def migrate(url=None):
    """Nâng database lên `head`. Trả về danh sách việc đã làm, để tool in ra cho người chạy."""
    engine = get_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    cfg = alembic_config(url)
    steps = []
    if "alembic_version" not in tables:
        if set(metadata.tables) <= tables:
            command.stamp(cfg, "head")
            steps.append("đánh dấu head: database dựng bằng build() của phiên bản này")
        elif "curricula" in tables:
            command.stamp(cfg, V1_REVISION)
            steps.append(f"đánh dấu {V1_REVISION}: database dựng ở lược đồ 3.0.0 (v1)")
    before = current_revision(url)
    command.upgrade(cfg, "head")
    after = current_revision(url)
    if before != after:
        steps.append(f"nâng {before or 'database trống'} -> {after}")
    return steps
