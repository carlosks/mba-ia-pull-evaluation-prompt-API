"""
Ambiente do Alembic. Usa a mesma DATABASE_URL da aplicação.

Comandos úteis:
    alembic upgrade head                      # aplica migrações
    alembic revision --autogenerate -m "..."  # cria migração a partir dos models
"""

from alembic import context

from app import models  # noqa: F401  (registra as tabelas no metadata)
from app.database import Base, DATABASE_URL, engine

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")

    if connection is not None:
        _run(connection)
        return

    with engine.connect() as connection:
        _run(connection)
        connection.commit()


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # batch mode permite ALTER TABLE no SQLite
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
