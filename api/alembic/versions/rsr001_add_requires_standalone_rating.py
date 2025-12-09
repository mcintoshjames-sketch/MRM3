"""add requires_standalone_rating to regions

Revision ID: rsr001_standalone_rating
Revises: mp001_is_dirty
Create Date: 2025-12-09 10:00:00.000000

This migration adds a requires_standalone_rating boolean flag to the regions table.
When enabled for a region, models deployed to that region require a region-specific
risk assessment before validation can progress to Review or Approval status.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'rsr001_standalone_rating'
down_revision: Union[str, None] = 'mp001_is_dirty'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('regions',
        sa.Column('requires_standalone_rating', sa.Boolean(), nullable=False,
                  server_default=sa.text('false'),
                  comment='When true, models deployed to this region require a region-specific risk assessment')
    )


def downgrade() -> None:
    op.drop_column('regions', 'requires_standalone_rating')
