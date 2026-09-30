"""Aceite dos Termos de Uso e Política de Privacidade

Revision ID: 0004_terms_acceptance
Revises: 0003_billing
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_terms_acceptance"
down_revision = "0003_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("terms_version", sa.String(), nullable=True))
        batch.add_column(sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("terms_accepted_at")
        batch.drop_column("terms_version")
