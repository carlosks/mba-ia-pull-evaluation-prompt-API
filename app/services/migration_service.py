from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import engine


def _column_exists(db_engine: Engine, table_name: str, column_name: str) -> bool:
    inspector = inspect(db_engine)

    if table_name not in inspector.get_table_names():
        return False

    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _table_exists(db_engine: Engine, table_name: str) -> bool:
    inspector = inspect(db_engine)
    return table_name in inspector.get_table_names()


def run_startup_migrations() -> None:
    """
    Executa migrações simples e idempotentes no startup da aplicação.

    Objetivo:
    - Evitar erro local quando app.db está antigo.
    - Criar colunas novas na tabela users.
    - Criar tabela usage_logs se não existir.
    """

    with engine.begin() as conn:
        if _table_exists(engine, "users"):
            additions = [
                (
                    "plan",
                    "ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'",
                ),
                (
                    "monthly_generation_limit",
                    "ALTER TABLE users ADD COLUMN monthly_generation_limit INTEGER DEFAULT 5",
                ),
                (
                    "is_active",
                    "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1",
                ),
                (
                    "is_admin",
                    "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",
                ),
                (
                    "created_at",
                    "ALTER TABLE users ADD COLUMN created_at TEXT",
                ),
            ]

            for column_name, sql in additions:
                if not _column_exists(engine, "users", column_name):
                    conn.execute(text(sql))

            conn.execute(
                text("UPDATE users SET plan='free' WHERE plan IS NULL OR plan=''")
            )
            conn.execute(
                text(
                    "UPDATE users SET monthly_generation_limit=5 "
                    "WHERE monthly_generation_limit IS NULL"
                )
            )
            conn.execute(
                text("UPDATE users SET is_active=1 WHERE is_active IS NULL")
            )
            conn.execute(
                text("UPDATE users SET is_admin=0 WHERE is_admin IS NULL")
            )

        if not _table_exists(engine, "usage_logs"):
            conn.execute(
                text(
                    """
                    CREATE TABLE usage_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        endpoint TEXT NOT NULL,
                        project_name TEXT,
                        status TEXT NOT NULL DEFAULT 'success',
                        created_at TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                    """
                )
            )

    print("Database migrations checked successfully.")
