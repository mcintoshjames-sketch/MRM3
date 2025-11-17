"""Add taxonomy tables

Revision ID: e6f47g9b0123
Revises: d5e36f8a9012
Create Date: 2024-01-16 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6f47g9b0123'
down_revision = 'd5e36f8a9012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create taxonomies table
    op.create_table(
        'taxonomies',
        sa.Column('taxonomy_id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create taxonomy_values table
    op.create_table(
        'taxonomy_values',
        sa.Column('value_id', sa.Integer(), primary_key=True, index=True),
        sa.Column('taxonomy_id', sa.Integer(), sa.ForeignKey('taxonomies.taxonomy_id'), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Add taxonomy columns to models table
    op.add_column('models', sa.Column('risk_tier_id', sa.Integer(), sa.ForeignKey('taxonomy_values.value_id'), nullable=True))
    op.add_column('models', sa.Column('validation_type_id', sa.Integer(), sa.ForeignKey('taxonomy_values.value_id'), nullable=True))


def downgrade() -> None:
    # Remove columns from models table
    op.drop_column('models', 'validation_type_id')
    op.drop_column('models', 'risk_tier_id')

    # Drop taxonomy tables
    op.drop_table('taxonomy_values')
    op.drop_table('taxonomies')
