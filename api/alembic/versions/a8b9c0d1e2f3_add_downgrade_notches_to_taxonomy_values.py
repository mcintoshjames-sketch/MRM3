"""Add downgrade_notches column to taxonomy_values

Revision ID: a8b9c0d1e2f3
Revises: aa1b2c3d4e5f
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8b9c0d1e2f3'
down_revision = 'aa1b2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade():
    # Add downgrade_notches column to taxonomy_values table
    # This column stores the number of notches to downgrade the scorecard outcome
    # when a model is in a given past-due bucket
    op.add_column(
        'taxonomy_values',
        sa.Column(
            'downgrade_notches',
            sa.Integer(),
            nullable=True,
            comment='Number of scorecard notches to downgrade for this past-due bucket (0-5)'
        )
    )


def downgrade():
    op.drop_column('taxonomy_values', 'downgrade_notches')
