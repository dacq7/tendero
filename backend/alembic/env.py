"""Entorno de migraciones Alembic (síncrono), conectado a la config de la app."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  — registra los modelos en SQLModel.metadata
from alembic import context
from app.core.config import settings

config = context.config

# La URL viene de nuestra config (env), nunca del alembic.ini. Si quien invoca
# Alembic ya fijó una URL real en la Config (p. ej. los tests, que apuntan a la
# base `tendero_test`), se respeta; el `alembic.ini` solo trae un placeholder
# `driver://...`. Así los tests no necesitan mutar el singleton `settings`.
_url = config.get_main_option("sqlalchemy.url")
if not _url or _url.startswith("driver://"):
    _url = settings.database_url
config.set_main_option("sqlalchemy.url", _url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
