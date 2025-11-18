"""add_region_id_to_validations

Revision ID: 8561686cdb50
Revises: 1b384f53a08c
Create Date: 2025-11-18 01:27:02.372022

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8561686cdb50'
down_revision: Union[str, None] = '1b384f53a08c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add region_id to validation_requests (nullable for backward compatibility)
    op.add_column('validation_requests', sa.Column('region_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_validation_requests_region', 'validation_requests', 'regions', ['region_id'], ['region_id'], ondelete='SET NULL')
    op.create_index(op.f('ix_validation_requests_region_id'), 'validation_requests', ['region_id'], unique=False)

    # Add region_id to validations (legacy table, for consistency)
    op.add_column('validations', sa.Column('region_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_validations_region', 'validations', 'regions', ['region_id'], ['region_id'], ondelete='SET NULL')
    op.create_index(op.f('ix_validations_region_id'), 'validations', ['region_id'], unique=False)


def downgrade() -> None:
    # Drop indexes and foreign keys for validations
    op.drop_index(op.f('ix_validations_region_id'), table_name='validations')
    op.drop_constraint('fk_validations_region', 'validations', type_='foreignkey')
    op.drop_column('validations', 'region_id')

    # Drop indexes and foreign keys for validation_requests
    op.drop_index(op.f('ix_validation_requests_region_id'), table_name='validation_requests')
    op.drop_constraint('fk_validation_requests_region', 'validation_requests', type_='foreignkey')
    op.drop_column('validation_requests', 'region_id')
