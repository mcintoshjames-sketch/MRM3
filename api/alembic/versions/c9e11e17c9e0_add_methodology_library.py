"""add_methodology_library

Revision ID: c9e11e17c9e0
Revises: d9e0f1g2h3i4
Create Date: 2025-12-05 15:08:52.007167

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c9e11e17c9e0'
down_revision: Union[str, None] = 'd9e0f1g2h3i4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create methodology_categories table
    op.create_table('methodology_categories',
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('category_id')
    )
    op.create_index(op.f('ix_methodology_categories_code'), 'methodology_categories', ['code'], unique=True)

    # Create methodologies table
    op.create_table('methodologies',
        sa.Column('methodology_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('variants', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['methodology_categories.category_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('methodology_id')
    )
    op.create_index(op.f('ix_methodologies_category_id'), 'methodologies', ['category_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_methodologies_category_id'), table_name='methodologies')
    op.drop_table('methodologies')
    op.drop_index(op.f('ix_methodology_categories_code'), table_name='methodology_categories')
    op.drop_table('methodology_categories')
