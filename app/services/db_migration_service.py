from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _table_exists(table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def _is_postgresql() -> bool:
    return engine.dialect.name == "postgresql"


def _is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"


def run_database_migrations() -> None:
    """
    Migração simples para manter compatibilidade entre SQLite local e PostgreSQL no Render.

    Esta rotina:
    - cria tabelas novas, como usage_logs;
    - adiciona colunas novas na tabela users quando ainda não existirem;
    - mantém usuários antigos com plano free.
    """

    Base.metadata.create_all(bind=engine)

    if not _table_exists("users"):
        return

    with engine.begin() as connection:
        if not _column_exists("users", "plan"):
            connection.execute(
                text("ALTER TABLE users ADD COLUMN plan VARCHAR")
            )

        if not _column_exists("users", "monthly_generation_limit"):
            connection.execute(
                text("ALTER TABLE users ADD COLUMN monthly_generation_limit INTEGER")
            )

        if not _column_exists("users", "is_active"):
            if _is_postgresql():
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN is_active BOOLEAN")
                )
            elif _is_sqlite():
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN is_active BOOLEAN")
                )
            else:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN is_active BOOLEAN")
                )

        if not _column_exists("users", "is_admin"):
            if _is_postgresql():
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN")
                )
            elif _is_sqlite():
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN")
                )
            else:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN")
                )

        if not _column_exists("users", "created_at"):
            if _is_postgresql():
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
                )
            elif _is_sqlite():
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN created_at DATETIME")
                )
            else:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
                )

        connection.execute(
            text("UPDATE users SET plan = 'free' WHERE plan IS NULL OR plan = ''")
        )

        connection.execute(
            text("UPDATE users SET monthly_generation_limit = 5 WHERE monthly_generation_limit IS NULL")
        )

        if _is_postgresql():
            connection.execute(
                text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
            )
            connection.execute(
                text("UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL")
            )
            connection.execute(
                text("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            )
        else:
            connection.execute(
                text("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
            )
            connection.execute(
                text("UPDATE users SET is_admin = 0 WHERE is_admin IS NULL")
            )
            connection.execute(
                text("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            )