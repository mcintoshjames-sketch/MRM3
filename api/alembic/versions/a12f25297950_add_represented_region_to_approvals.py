"""add_represented_region_to_approvals

Revision ID: a12f25297950
Revises: ef029e1d2f99
Create Date: 2025-11-22 04:42:02.500541

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a12f25297950'
down_revision: Union[str, None] = 'ef029e1d2f99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add represented_region_id column to validation_approvals
    # This captures what role the approver was representing at approval time
    # NULL = Global Approver, non-NULL = Regional Approver for that region
    op.add_column('validation_approvals',
        sa.Column('represented_region_id', sa.Integer(), nullable=True,
                  comment='Region the approver was representing at approval time (NULL for Global Approver)')
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_validation_approvals_represented_region',
        'validation_approvals',
        'regions',
        ['represented_region_id'],
        ['region_id'],
        ondelete='SET NULL'
    )

    # Create index for query performance
    op.create_index(
        'ix_validation_approvals_represented_region_id',
        'validation_approvals',
        ['represented_region_id']
    )

    # Data migration: populate represented_region_id based on existing region_id
    # For Regional approvals, the represented_region_id should match region_id
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE validation_approvals
        SET represented_region_id = region_id
        WHERE approval_type = 'Regional' AND region_id IS NOT NULL
    """))


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_validation_approvals_represented_region_id', table_name='validation_approvals')

    # Drop foreign key constraint
    op.drop_constraint('fk_validation_approvals_represented_region', 'validation_approvals', type_='foreignkey')

    # Drop column
    op.drop_column('validation_approvals', 'represented_region_id')
