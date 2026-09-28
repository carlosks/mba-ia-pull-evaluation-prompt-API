from __future__ import annotations

import logging
import secrets
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.config import CREATE_DEV_ADMIN, DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD
from app.database import engine

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


def _patch_legacy_database() -> None:
    """
    Ajustes para bancos criados antes do Alembic, deixando-os iguais à
    revisão 0001_baseline. Roda uma única vez: depois disso o banco é
    marcado (stamp) e só o Alembic mexe no esquema.
    """

    if _table_exists(engine, "users"):
        # Inspeciona ANTES de abrir a transação: no Postgres o ALTER TABLE
        # bloqueia a tabela e uma inspeção em outra conexão ficaria esperando.
        existing_columns = {
            column["name"]: column["type"]
            for column in inspect(engine).get_columns("users")
        }
    else:
        existing_columns = None

    with engine.begin() as conn:
        if existing_columns is not None:
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
                    "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
                ),
                (
                    "is_admin",
                    "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE",
                ),
                (
                    "created_at",
                    "ALTER TABLE users ADD COLUMN created_at TEXT",
                ),
            ]

            for column_name, sql in additions:
                if column_name not in existing_columns:
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
            for column_name, default in (("is_active", True), ("is_admin", False)):
                column_type = existing_columns.get(column_name)
                # Coluna antiga criada como INTEGER: grava 1/0 em vez de true/false.
                is_integer = column_type is not None and "INT" in str(column_type).upper()
                value = int(default) if is_integer else default
                conn.execute(
                    text(f"UPDATE users SET {column_name}=:v WHERE {column_name} IS NULL"),
                    {"v": value},
                )

    if not _table_exists(engine, "usage_logs"):
        # Só as colunas da revisão 0001; as de custo chegam pela 0002.
        import sqlalchemy as sa

        metadata = sa.MetaData()
        sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
        usage_logs = sa.Table(
            "usage_logs",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("endpoint", sa.String, nullable=False),
            sa.Column("project_name", sa.String),
            sa.Column("status", sa.String, nullable=False, server_default="success"),
            sa.Column("created_at", sa.DateTime, index=True),
        )
        usage_logs.create(bind=engine)


def _alembic_config():
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "alembic"))
    return config


def run_startup_migrations() -> None:
    """
    Deixa o banco na versão mais recente no startup da aplicação.

    - Banco novo (vazio): o Alembic cria tudo.
    - Banco antigo, anterior ao Alembic: aplica os ajustes legados,
      marca como 0001_baseline e depois aplica o restante.
    - Banco já versionado: aplica só as migrações pendentes.
    """
    from alembic import command

    config = _alembic_config()

    has_version_table = _table_exists(engine, "alembic_version")
    is_legacy_database = _table_exists(engine, "users") and not has_version_table

    if is_legacy_database:
        logger.info("Banco anterior ao Alembic detectado; aplicando ajustes legados.")
        _patch_legacy_database()
        command.stamp(config, "0001_baseline")

    command.upgrade(config, "head")

    ensure_development_admin_user(engine)
    logger.info("Database migrations checked successfully.")
