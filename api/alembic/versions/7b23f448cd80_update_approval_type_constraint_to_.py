"""update_approval_type_constraint_to_allow_conditional

Revision ID: 7b23f448cd80
Revises: 6a7ec59943ec
Create Date: 2025-11-24 23:08:58.408051

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b23f448cd80'
down_revision: Union[str, None] = '6a7ec59943ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old constraint that only allows 'Global' and 'Regional'
    op.drop_constraint('chk_approval_type', 'validation_approvals', type_='check')

    # Create new constraint allowing 'Conditional' as well
    op.create_check_constraint(
        'chk_approval_type',
        'validation_approvals',
        "approval_type IN ('Global', 'Regional', 'Conditional')"
    )

    # Drop the regional approval constraint that doesn't account for Conditional
    op.drop_constraint('chk_regional_approval_has_region', 'validation_approvals', type_='check')

    # Create new constraint allowing Conditional approvals without region_id
    op.create_check_constraint(
        'chk_regional_approval_has_region',
        'validation_approvals',
        "(approval_type = 'Regional' AND region_id IS NOT NULL) OR (approval_type = 'Global' AND region_id IS NULL) OR (approval_type = 'Conditional' AND region_id IS NULL)"
    )


def downgrade() -> None:
    # Drop the new regional constraint
    op.drop_constraint('chk_regional_approval_has_region', 'validation_approvals', type_='check')

    # Recreate the old regional constraint (only Global and Regional)
    op.create_check_constraint(
        'chk_regional_approval_has_region',
        'validation_approvals',
        "(approval_type = 'Regional' AND region_id IS NOT NULL) OR (approval_type = 'Global' AND region_id IS NULL)"
    )

    # Drop the new approval_type constraint
    op.drop_constraint('chk_approval_type', 'validation_approvals', type_='check')

    # Recreate the old approval_type constraint (only Global and Regional)
    op.create_check_constraint(
        'chk_approval_type',
        'validation_approvals',
        "approval_type IN ('Global', 'Regional')"
    )
