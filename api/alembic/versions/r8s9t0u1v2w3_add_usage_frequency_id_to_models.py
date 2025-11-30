"""Add usage_frequency_id to models.

Revision ID: r8s9t0u1v2w3
Revises: 64cb4ff2a1b0
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'r8s9t0u1v2w3'
down_revision = '64cb4ff2a1b0'
branch_labels = None
depends_on = None


def upgrade():
    # Add usage_frequency_id column to models table
    op.add_column(
        'models',
        sa.Column(
            'usage_frequency_id',
            sa.Integer(),
            sa.ForeignKey('taxonomy_values.value_id'),
            nullable=True,
            comment='How frequently the model is typically used (Daily, Monthly, Quarterly, Annually)'
        )
    )


def downgrade():
    op.drop_column('models', 'usage_frequency_id')
