"""add_regions_table

Revision ID: 38b64e3a491e
Revises: 6105c56a44ec
Create Date: 2025-11-18 00:51:28.171921

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38b64e3a491e'
down_revision: Union[str, None] = '6105c56a44ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create regions table
    op.create_table(
        'regions',
        sa.Column('region_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('region_id')
    )
    op.create_index(op.f('ix_regions_region_id'), 'regions', ['region_id'], unique=False)
    op.create_index(op.f('ix_regions_code'), 'regions', ['code'], unique=True)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_regions_code'), table_name='regions')
    op.drop_index(op.f('ix_regions_region_id'), table_name='regions')
    # Drop table
    op.drop_table('regions')
