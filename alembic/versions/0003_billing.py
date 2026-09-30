"""Assinaturas e eventos de cobrança (Asaas)

Revision ID: 0003_billing
Revises: 0002_jobs_and_llm_cost
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_billing"
down_revision = "0002_jobs_and_llm_cost"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False, server_default="asaas"),
        sa.Column("provider_customer_id", sa.String()),
        sa.Column("provider_subscription_id", sa.String()),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("invoice_url", sa.String()),
        sa.Column("current_period_end", sa.DateTime()),
        sa.Column("canceled_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_provider_customer_id", "subscriptions", ["provider_customer_id"])
    op.create_index(
        "ix_subscriptions_provider_subscription_id",
        "subscriptions",
        ["provider_subscription_id"],
        unique=True,
    )

    op.create_table(
        "billing_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False, server_default="asaas"),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text()),
        sa.Column("received_at", sa.DateTime()),
    )
    op.create_index("ix_billing_events_event_type", "billing_events", ["event_type"])
    op.create_index("ix_billing_events_received_at", "billing_events", ["received_at"])


def downgrade() -> None:
    op.drop_table("billing_events")
    op.drop_table("subscriptions")
