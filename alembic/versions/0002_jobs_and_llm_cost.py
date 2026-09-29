"""Fila de gerações e custo do LLM por uso

Revision ID: 0002_jobs_and_llm_cost
Revises: 0001_baseline
Create Date: 2026-09-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_jobs_and_llm_cost"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("usage_logs") as batch:
        batch.add_column(sa.Column("model", sa.String()))
        batch.add_column(sa.Column("input_tokens", sa.Integer()))
        batch.add_column(sa.Column("output_tokens", sa.Integer()))
        batch.add_column(sa.Column("cost_usd", sa.Float()))
        batch.add_column(sa.Column("duration_ms", sa.Integer()))

    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("bug", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("project_name", sa.String()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
    )
    op.create_index("ix_generation_jobs_user_id", "generation_jobs", ["user_id"])
    op.create_index("ix_generation_jobs_status", "generation_jobs", ["status"])
    op.create_index("ix_generation_jobs_created_at", "generation_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_table("generation_jobs")

    with op.batch_alter_table("usage_logs") as batch:
        batch.drop_column("duration_ms")
        batch.drop_column("cost_usd")
        batch.drop_column("output_tokens")
        batch.drop_column("input_tokens")
        batch.drop_column("model")
