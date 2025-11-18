"""add_model_regions_table

Revision ID: 1b384f53a08c
Revises: 860eefd8f744
Create Date: 2025-11-18 01:20:54.220880

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b384f53a08c'
down_revision: Union[str, None] = '860eefd8f744'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create model_regions table
    op.create_table(
        'model_regions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('region_id', sa.Integer(), nullable=False),
        sa.Column('shared_model_owner_id', sa.Integer(), nullable=True),
        sa.Column('regional_risk_level', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_model_owner_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.UniqueConstraint('model_id', 'region_id', name='uq_model_region')
    )
    op.create_index(op.f('ix_model_regions_model_id'), 'model_regions', ['model_id'], unique=False)
    op.create_index(op.f('ix_model_regions_region_id'), 'model_regions', ['region_id'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_model_regions_region_id'), table_name='model_regions')
    op.drop_index(op.f('ix_model_regions_model_id'), table_name='model_regions')
    # Drop table
    op.drop_table('model_regions')
