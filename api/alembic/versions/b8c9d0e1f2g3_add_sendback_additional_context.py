"""Add additional_context column to validation_status_history for send-back feature.

Revision ID: b8c9d0e1f2g3
Revises: a7b8c9d0e1f2
Create Date: 2025-12-06

This migration adds the additional_context column to validation_status_history
for storing JSON data such as revision snapshots when approvers send back
validation requests for revision.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8c9d0e1f2g3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'validation_status_history',
        sa.Column(
            'additional_context',
            sa.Text(),
            nullable=True,
            comment='JSON storing action-specific details (e.g., revision snapshots for send-back)'
        )
    )


def downgrade() -> None:
    op.drop_column('validation_status_history', 'additional_context')
