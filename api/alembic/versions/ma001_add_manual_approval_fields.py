"""add_manual_approval_fields

Revision ID: ma001_add_manual_approval_fields
Revises: k1l2m3n4o5p6
Create Date: 2026-02-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ma001_add_manual_approval_fields'
down_revision: Union[str, None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'validation_approvals',
        sa.Column('manually_added_by_id', sa.Integer(), nullable=True)
    )
    op.add_column(
        'validation_approvals',
        sa.Column('manual_add_reason', sa.Text(), nullable=True)
    )
    op.add_column(
        'validation_approvals',
        sa.Column('manually_added_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'validation_approvals',
        sa.Column('assigned_approver_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_validation_approvals_manually_added_by',
        'validation_approvals',
        'users',
        ['manually_added_by_id'],
        ['user_id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_validation_approvals_assigned_approver',
        'validation_approvals',
        'users',
        ['assigned_approver_id'],
        ['user_id'],
        ondelete='SET NULL'
    )
    op.create_index(
        'ix_validation_approvals_assigned_approver_id',
        'validation_approvals',
        ['assigned_approver_id']
    )

    op.drop_constraint('chk_approval_type', 'validation_approvals', type_='check')
    op.create_check_constraint(
        'chk_approval_type',
        'validation_approvals',
        "approval_type IN ('Global', 'Regional', 'Conditional', 'Manual-Role', 'Manual-User')"
    )
    op.drop_constraint('chk_regional_approval_has_region', 'validation_approvals', type_='check')
    op.create_check_constraint(
        'chk_regional_approval_has_region',
        'validation_approvals',
        "(approval_type = 'Regional' AND region_id IS NOT NULL) OR "
        "(approval_type IN ('Global', 'Conditional', 'Manual-Role', 'Manual-User') AND region_id IS NULL)"
    )


def downgrade() -> None:
    op.drop_constraint('chk_regional_approval_has_region', 'validation_approvals', type_='check')
    op.create_check_constraint(
        'chk_regional_approval_has_region',
        'validation_approvals',
        "(approval_type = 'Regional' AND region_id IS NOT NULL) OR "
        "(approval_type IN ('Global', 'Conditional') AND region_id IS NULL)"
    )
    op.drop_constraint('chk_approval_type', 'validation_approvals', type_='check')
    op.create_check_constraint(
        'chk_approval_type',
        'validation_approvals',
        "approval_type IN ('Global', 'Regional', 'Conditional')"
    )

    op.drop_index('ix_validation_approvals_assigned_approver_id', table_name='validation_approvals')
    op.drop_constraint('fk_validation_approvals_assigned_approver', 'validation_approvals', type_='foreignkey')
    op.drop_constraint('fk_validation_approvals_manually_added_by', 'validation_approvals', type_='foreignkey')
    op.drop_column('validation_approvals', 'assigned_approver_id')
    op.drop_column('validation_approvals', 'manually_added_at')
    op.drop_column('validation_approvals', 'manual_add_reason')
    op.drop_column('validation_approvals', 'manually_added_by_id')
