"""Môi trường Alembic.

Lược đồ đích là `src/data/db/schema.py`, nguồn sự thật duy nhất. Địa chỉ database lấy theo đúng thứ tự của
`src/data/db/build.py`: tham số do `src/data/db/migrate.py` truyền vào, rồi `DATABASE_URL`, rồi mặc định của
docker-compose. Không đặt `sqlalchemy.url` trong `alembic.ini`, để mật khẩu không bao giờ nằm trong repo.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from src.data.db.build import database_url
from src.data.db.schema import metadata

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = metadata


def _configure(**kwargs):
    context.configure(target_metadata=target_metadata, compare_type=True, compare_server_default=True, **kwargs)


def run_migrations_offline():
    _configure(url=config.attributes.get("url") or database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(config.attributes.get("url") or database_url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        _configure(connection=conn)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
