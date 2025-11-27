"""Add KPM tables

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2025-01-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create kpm_categories table
    op.create_table(
        'kpm_categories',
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('category_id'),
        sa.UniqueConstraint('code')
    )

    # Create kpms table
    op.create_table(
        'kpms',
        sa.Column('kpm_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('calculation', sa.Text(), nullable=True),
        sa.Column('interpretation', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['category_id'], ['kpm_categories.category_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('kpm_id')
    )
    op.create_index('ix_kpms_category_id', 'kpms', ['category_id'])


def downgrade() -> None:
    op.drop_index('ix_kpms_category_id', table_name='kpms')
    op.drop_table('kpms')
    op.drop_table('kpm_categories')
