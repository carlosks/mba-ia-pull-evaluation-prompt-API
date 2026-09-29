"""Estrutura inicial (usuários, projetos e registro de uso)

Bancos criados antes do Alembic já têm estas tabelas: o startup
marca esta revisão como aplicada (stamp) em vez de executá-la.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("monthly_generation_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bug", sa.Text(), nullable=False),
        sa.Column("user_story", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", sa.Text()),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("score", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("zip_path", sa.String()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_projects_id", "projects", ["id"])

    op.create_table(
        "usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("project_name", sa.String()),
        sa.Column("status", sa.String(), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_usage_logs_id", "usage_logs", ["id"])
    op.create_index("ix_usage_logs_created_at", "usage_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("usage_logs")
    op.drop_table("projects")
    op.drop_table("users")
