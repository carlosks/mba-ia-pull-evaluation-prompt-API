from __future__ import annotations

import os

from passlib.context import CryptContext
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



pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])


def _is_sqlite_database() -> bool:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    return database_url.startswith("sqlite")


def _should_create_dev_admin() -> bool:
    value = os.getenv("CREATE_DEV_ADMIN")

    if value is None:
        return _is_sqlite_database()

    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def ensure_development_admin_user(engine: Engine) -> None:
    """
    Cria ou atualiza um usuário admin local para ambiente de desenvolvimento.

    Por segurança, a criação automática só acontece quando:
    - CREATE_DEV_ADMIN=true; ou
    - DATABASE_URL é SQLite e CREATE_DEV_ADMIN não foi definido.

    Em produção, use CREATE_DEV_ADMIN=false.
    """

    if not _should_create_dev_admin():
        return

    admin_email = os.getenv("DEV_ADMIN_EMAIL", "admin@exemplo.com")
    admin_password = os.getenv("DEV_ADMIN_PASSWORD", "123456")

    with engine.begin() as conn:
        if not _table_exists(engine, "users"):
            return

        existing_user = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": admin_email},
        ).fetchone()

        hashed_password = _hash_password(admin_password)

        if existing_user:
            conn.execute(
                text(
                    """
                    UPDATE users
                    SET hashed_password = :hashed_password,
                        plan = 'pro',
                        monthly_generation_limit = 50,
                        is_active = 1,
                        is_admin = 1
                    WHERE email = :email
                    """
                ),
                {
                    "email": admin_email,
                    "hashed_password": hashed_password,
                },
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO users (
                        email,
                        hashed_password,
                        plan,
                        monthly_generation_limit,
                        is_active,
                        is_admin
                    )
                    VALUES (
                        :email,
                        :hashed_password,
                        'pro',
                        50,
                        1,
                        1
                    )
                    """
                ),
                {
                    "email": admin_email,
                    "hashed_password": hashed_password,
                },
            )

    print(f"Development admin user checked successfully: {admin_email}")

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

    ensure_development_admin_user(engine)
    print("Database migrations checked successfully.")
