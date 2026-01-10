"""add_external_project_id_to_validation_requests

Revision ID: n5o6p7q8r9s0
Revises: x4y5z6a7b8c9
Create Date: 2025-12-01
"""

from alembic import op
import sqlalchemy as sa


revision = "n5o6p7q8r9s0"
down_revision = "x4y5z6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "validation_requests",
        sa.Column(
            "external_project_id",
            sa.String(length=36),
            nullable=True,
            comment="External project identifier",
        ),
    )


def downgrade() -> None:
    op.drop_column("validation_requests", "external_project_id")
