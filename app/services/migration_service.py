from __future__ import annotations

import logging
import secrets

from passlib.context import CryptContext
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.config import CREATE_DEV_ADMIN, DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD
from app.database import Base, engine

logger = logging.getLogger("app.migrations")


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


def ensure_development_admin_user(engine: Engine) -> None:
    """
    Cria um usuário admin local, apenas em desenvolvimento.

    Regras de segurança:
    - Nunca roda em produção (ver app.config.CREATE_DEV_ADMIN).
    - Só roda com CREATE_DEV_ADMIN=true explícito.
    - Se DEV_ADMIN_PASSWORD não for informada, gera uma senha aleatória
      e a mostra uma única vez no log.
    - Se o usuário já existir, a senha dele NÃO é alterada.
    """

    if not CREATE_DEV_ADMIN:
        return

    if not _table_exists(engine, "users"):
        return

    admin_email = DEV_ADMIN_EMAIL

    with engine.begin() as conn:
        existing_user = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": admin_email},
        ).fetchone()

        if existing_user:
            conn.execute(
                text("UPDATE users SET is_admin = :true, is_active = :true WHERE email = :email"),
                {"email": admin_email, "true": True},
            )
            logger.info("Admin de desenvolvimento já existe: %s", admin_email)
            return

        admin_password = DEV_ADMIN_PASSWORD or secrets.token_urlsafe(12)

        conn.execute(
            text(
                """
                INSERT INTO users (
                    email, hashed_password, plan,
                    monthly_generation_limit, is_active, is_admin
                )
                VALUES (:email, :hashed_password, 'admin', -1, :true, :true)
                """
            ),
            {
                "email": admin_email,
                "hashed_password": _hash_password(admin_password),
                "true": True,
            },
        )

    if DEV_ADMIN_PASSWORD:
        logger.warning("Admin de desenvolvimento criado: %s", admin_email)
    else:
        logger.warning(
            "Admin de desenvolvimento criado: %s | senha gerada: %s "
            "(defina DEV_ADMIN_PASSWORD para escolher a senha)",
            admin_email,
            admin_password,
        )


def run_startup_migrations() -> None:
    """
    Executa migrações simples e idempotentes no startup da aplicação.

    Objetivo:
    - Evitar erro local quando app.db está antigo.
    - Criar colunas novas na tabela users.
    - Criar tabela usage_logs se não existir.
    """

    # Cria as tabelas que ainda não existem (banco novo).
    # Importar models registra todas as tabelas no Base.metadata.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

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
    logger.info("Database migrations checked successfully.")
