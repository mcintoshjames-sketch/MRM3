"""Add model_type and regulatory_categories

Revision ID: g8h69i1d2345
Revises: f7g58h0c1234
Create Date: 2024-01-17 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g8h69i1d2345'
down_revision = 'f7g58h0c1234'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add model_type_id column to models table
    op.add_column('models', sa.Column('model_type_id', sa.Integer(), sa.ForeignKey('taxonomy_values.value_id'), nullable=True))

    # Create association table for regulatory categories (many-to-many)
    op.create_table(
        'model_regulatory_categories',
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('value_id', sa.Integer(), sa.ForeignKey('taxonomy_values.value_id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('model_regulatory_categories')
    op.drop_column('models', 'model_type_id')
