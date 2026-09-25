import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.models import Base  # noqa: F401 (model 등록을 위해 반드시 import)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 접속 주소는 alembic.ini에 적지 않는다 ─ ini는 Git에 추적되므로 비밀번호가 노출된다.
# 그래서 비어 있으면 .env 값으로 채우고, 외부에서 주소를 넣어준 경우(= 테스트)엔 그 값을 존중한다.
# "게임 장르가 0개일 때만 채운다"와 똑같은 패턴이다 ─ 빈칸만 채우고, 남이 정해둔 값은 건드리지 않는다.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# Model의 MetaData(출석부)를 넘겨야 autogenerate가 테이블 차이를 계산할 수 있다
# app.models를 import하는 것만으로 모든 Model이 이 출석부에 등록된다
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
