"""add_external_model_id

Revision ID: 7f3a1c2d4e5f
Revises: 02ece2c0ef80
Create Date: 2026-01-04
"""

from alembic import op
import sqlalchemy as sa


revision = "7f3a1c2d4e5f"
down_revision = "02ece2c0ef80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "models",
        sa.Column("external_model_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("models", "external_model_id")
