"""drop_scorecard_effective_date

Revision ID: z6a7b8c9d0e1
Revises: 451cbddc8250
Create Date: 2025-12-02 05:00:00.000000

This migration removes the effective_date column from scorecard_config_versions
as it served no practical purpose (was cosmetic/documentation only).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'z6a7b8c9d0e1'
down_revision: Union[str, None] = '451cbddc8250'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the effective_date column
    op.drop_column('scorecard_config_versions', 'effective_date')


def downgrade() -> None:
    # Add back the effective_date column with a default of today
    op.add_column('scorecard_config_versions',
        sa.Column('effective_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE'),
                  comment='Date this version becomes effective')
    )
    # Remove the server default after backfilling
    op.alter_column('scorecard_config_versions', 'effective_date', server_default=None)
