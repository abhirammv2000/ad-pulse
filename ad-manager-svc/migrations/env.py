"""Alembic environment for the ad manager's Postgres schema.

The database URL comes from DATABASE_URL, the same variable the service reads, through the same function, so a
migration run and the service always talk to the same database with the same driver. The models come from
app.models, which registers every table on Base.metadata.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models import Base
from config.db import _get_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic reads this file with a config parser, where % starts an interpolation, so a percent-encoded password in
# the URL has to have its % doubled.
config.set_main_option("sqlalchemy.url", _get_database_url().replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Write the SQL for a migration to the output instead of running it (`alembic upgrade head --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
