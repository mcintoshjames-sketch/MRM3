"""add_regional_model_implementations

Revision ID: 7b44e960ad31
Revises: 4869cf03f134
Create Date: 2025-11-18 00:38:24.036286

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b44e960ad31'
down_revision: Union[str, None] = '4869cf03f134'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create regional_model_implementations table
    op.create_table(
        'regional_model_implementations',
        sa.Column('regional_model_impl_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('region_id', sa.Integer(), nullable=False),
        sa.Column('shared_model_owner_id', sa.Integer(), nullable=True),
        sa.Column('local_identifier', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('decommission_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('regional_model_impl_id'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['shared_model_owner_id'], ['users.user_id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_regional_model_implementations_model_id'), 'regional_model_implementations', ['model_id'], unique=False)
    op.create_index(op.f('ix_regional_model_implementations_region_id'), 'regional_model_implementations', ['region_id'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_regional_model_implementations_region_id'), table_name='regional_model_implementations')
    op.drop_index(op.f('ix_regional_model_implementations_model_id'), table_name='regional_model_implementations')
    # Drop table
    op.drop_table('regional_model_implementations')
