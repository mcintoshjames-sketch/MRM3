"""add_region_id_and_approval_type_to_validation_approvals

Revision ID: c26020fa6b4d
Revises: 628a8ac6b2cd
Create Date: 2025-11-21 21:18:54.732515

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c26020fa6b4d'
down_revision: Union[str, None] = '628a8ac6b2cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add approval_type column with default value 'Global'
    op.add_column('validation_approvals',
        sa.Column('approval_type', sa.String(20), nullable=False, server_default='Global')
    )

    # Add CHECK constraint for approval_type
    op.create_check_constraint(
        'chk_approval_type',
        'validation_approvals',
        "approval_type IN ('Global', 'Regional')"
    )

    # Add region_id column (nullable because Global approvals won't have a region)
    op.add_column('validation_approvals',
        sa.Column('region_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint to regions table
    op.create_foreign_key(
        'fk_validation_approvals_region_id',
        'validation_approvals', 'regions',
        ['region_id'], ['region_id']
    )

    # Add CHECK constraint: Regional approvals must have region_id, Global approvals must not
    op.create_check_constraint(
        'chk_regional_approval_has_region',
        'validation_approvals',
        "(approval_type = 'Regional' AND region_id IS NOT NULL) OR (approval_type = 'Global' AND region_id IS NULL)"
    )

    # Add index on region_id for query performance (partial index for non-null values)
    op.create_index(
        'idx_validation_approvals_region',
        'validation_approvals',
        ['region_id'],
        postgresql_where=sa.text('region_id IS NOT NULL')
    )


def downgrade() -> None:
    # Remove in reverse order
    op.drop_index('idx_validation_approvals_region', 'validation_approvals')
    op.drop_constraint('chk_regional_approval_has_region', 'validation_approvals', type_='check')
    op.drop_constraint('fk_validation_approvals_region_id', 'validation_approvals', type_='foreignkey')
    op.drop_column('validation_approvals', 'region_id')
    op.drop_constraint('chk_approval_type', 'validation_approvals', type_='check')
    op.drop_column('validation_approvals', 'approval_type')
